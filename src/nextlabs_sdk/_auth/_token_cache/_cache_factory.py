from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from nextlabs_sdk._auth._token_cache._console_io import ConsoleIO
from nextlabs_sdk._auth._token_cache._encrypted_file_token_cache import (
    EncryptedFileTokenCache,
)
from nextlabs_sdk._auth._token_cache._env_passphrase_source import (
    EnvVarPassphraseSource,
)
from nextlabs_sdk._auth._token_cache._file_token_cache import (
    FileTokenCache,
    _default_path,
)
from nextlabs_sdk._auth._token_cache._interactive_passphrase_source import (
    InteractivePassphraseSource,
)
from nextlabs_sdk._auth._token_cache._keyring_passphrase_source import (
    KeyringPassphraseSource,
)
from nextlabs_sdk._auth._token_cache._passphrase_resolver import (
    PassphraseResolver,
)
from nextlabs_sdk._auth._token_cache._secret_box import SecretBox, read_header
from nextlabs_sdk._auth._token_cache._token_cache import TokenCache
from nextlabs_sdk.exceptions import TokenCacheError

_DISABLE_ENCRYPTION_ENV = "NEXTLABS_DISABLE_TOKEN_ENCRYPTION"
_PLAINTEXT_WARNING = (
    "warning: token cache is stored UNENCRYPTED; set NEXTLABS_MASTER_PASSWORD "
    "to encrypt it, or NEXTLABS_DISABLE_TOKEN_ENCRYPTION=1 to silence this warning"
)
_CONFIRM_WARNING = (
    "warning: no passphrase source is available, so the token cache would be "
    "stored UNENCRYPTED. Set NEXTLABS_MASTER_PASSWORD or configure an OS keyring "
    "to encrypt it later."
)
_CONFIRM_PROMPT = "Store the token cache unencrypted anyway? [y/N]: "

_WARNED = False


def build_token_cache(
    *,
    path: Path | str | None = None,
    env: Mapping[str, str] = os.environ,
    console: ConsoleIO | None = None,
) -> TokenCache:
    """Build a token cache, encrypting when a passphrase source is present.

    Sources are consulted in order: ``NEXTLABS_MASTER_PASSWORD``, the OS
    keyring, then an interactive TTY passphrase prompt. With no source and a
    TTY present the caller is warned and asked to confirm plaintext storage;
    declining raises :class:`TokenCacheError` without writing anything. With no
    source and no TTY the cache falls back to plaintext and emits a single
    process-wide warning to stderr; it never aborts. Setting
    ``NEXTLABS_DISABLE_TOKEN_ENCRYPTION=1`` silences the non-interactive warning.
    """
    console = console or ConsoleIO()
    resolver = PassphraseResolver(
        sources=(
            EnvVarPassphraseSource(),
            KeyringPassphraseSource(),
            InteractivePassphraseSource(console),
        )
    )
    material, _label = resolver.resolve(env)
    cache_path = _default_path() if path is None else Path(path)

    if material is not None:
        return EncryptedFileTokenCache(path=cache_path, kek_source=material)

    if console.isatty():
        return _confirm_plaintext_or_abort(console, cache_path)

    _warn_plaintext_once(env)
    return FileTokenCache(path=cache_path)


def _confirm_plaintext_or_abort(console: ConsoleIO, cache_path: Path) -> TokenCache:
    """Gate plaintext storage behind a confirmation on the controlling terminal.

    An unusable terminal cannot be prompted, so it degrades to plaintext rather
    than aborting, honouring the "encrypt when possible, never abort" policy.
    """
    print(_CONFIRM_WARNING, file=sys.stderr)
    try:
        confirmed = console.confirm(_CONFIRM_PROMPT)
    except OSError:
        return FileTokenCache(path=cache_path)
    if confirmed:
        return FileTokenCache(path=cache_path)
    raise TokenCacheError()


@dataclass(frozen=True)
class CacheStatus:
    """Observed state of the token cache file, reported without unlocking."""

    path: Path
    state: str
    source: str
    suite_id: int | None


def inspect_token_cache(
    *,
    path: Path | str | None = None,
    env: Mapping[str, str] = os.environ,
) -> CacheStatus:
    """Report the cache file's state without deriving any key or prompting.

    Resolves only the passphrase *source label* (never the material) and
    parses the envelope header bytes, so an encrypted cache is inspected
    without running Argon2 or unlocking it.
    """
    cache_path = _default_path() if path is None else Path(path)
    source = PassphraseResolver().peek(env)
    if not cache_path.exists():
        return CacheStatus(cache_path, "absent", source, None)
    blob = cache_path.read_bytes()
    if not SecretBox.is_encrypted(blob):
        return CacheStatus(cache_path, "plaintext", source, None)
    header = read_header(blob)
    return CacheStatus(cache_path, "encrypted", source, header.suite_id)


def _warn_plaintext_once(env: Mapping[str, str]) -> None:
    if env.get(_DISABLE_ENCRYPTION_ENV) == "1" or _WARNED:
        return
    print(_PLAINTEXT_WARNING, file=sys.stderr)
    globals()["_WARNED"] = True
