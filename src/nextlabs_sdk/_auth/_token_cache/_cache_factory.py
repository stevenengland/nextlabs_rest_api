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
from nextlabs_sdk._auth._token_cache._plaintext_ack_store import (
    PlaintextAckStore,
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

_HINT_FRESH = (
    "No token cache yet; it will be created at {path}. It can be encrypted at "
    "rest, but no passphrase source is set (NEXTLABS_MASTER_PASSWORD or an OS "
    "keyring). See the project's online documentation for details."
)
_HINT_LEGACY_PLAINTEXT = (
    "Your existing token cache at {path} is UNENCRYPTED and may contain "
    "access/refresh tokens in plain text. Set NEXTLABS_MASTER_PASSWORD or an OS "
    "keyring to re-encrypt it on the next write. See the project's online "
    "documentation for details."
)
_HINT_LOCKOUT = (
    "Your token cache at {path} is ENCRYPTED but no passphrase source is "
    "available to unlock it. Set the original NEXTLABS_MASTER_PASSWORD / "
    "keyring, or delete {path} to start fresh. See the project's online "
    "documentation for details."
)
_REMEMBER_PROMPT = "Remember this choice so I stop asking? [Y/n]: "
_SAVED_NOTICE = (
    "Saved. The CLI won't ask again. To re-enable encryption, set "
    "NEXTLABS_MASTER_PASSWORD or an OS keyring; nextlabs auth status shows the "
    "cache location and current choice."
)

_WARNED = False


def build_token_cache(
    *,
    path: Path | str | None = None,
    env: Mapping[str, str] = os.environ,
    console: ConsoleIO | None = None,
    ack_store: PlaintextAckStore | None = None,
) -> TokenCache:
    """Build a token cache, encrypting when a passphrase source is present.

    Sources are consulted in order: ``NEXTLABS_MASTER_PASSWORD``, the OS
    keyring, then an interactive TTY passphrase prompt. With no source and a
    TTY present the caller is warned and asked to confirm plaintext storage;
    declining raises :class:`TokenCacheError` without writing anything. With no
    source and no TTY the cache falls back to plaintext and emits a single
    process-wide warning to stderr; it never aborts. Setting
    ``NEXTLABS_DISABLE_TOKEN_ENCRYPTION=1`` silences the non-interactive warning.

    When ``ack_store`` is supplied and reports a remembered plaintext choice,
    the no-source TTY branch returns a plaintext cache silently. It is consulted
    only when no source resolves, so configuring a passphrase later upgrades to
    encryption without resetting the remembered choice.
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
        return _confirm_plaintext_or_abort(console, cache_path, env, ack_store)

    _warn_plaintext_once(env)
    return FileTokenCache(path=cache_path)


def _confirm_plaintext_or_abort(
    console: ConsoleIO,
    cache_path: Path,
    env: Mapping[str, str],
    ack_store: PlaintextAckStore | None,
) -> TokenCache:
    """Gate plaintext storage behind a confirmation on the controlling terminal.

    Emits a state-aware hint first: a first-time hint for an absent cache and a
    plaintext-exposure hint for an existing unencrypted one, both falling
    through to the confirm gate. An encrypted cache that no source can unlock is
    a lockout: the hint is shown and the build aborts without touching the file,
    so the encrypted tokens are never overwritten with plaintext.

    A remembered plaintext choice short-circuits the hint and confirm gate, but
    only after the lockout check, so acknowledging plaintext never clobbers an
    existing encrypted cache. On confirmation the caller is offered a one-time
    prompt to remember the choice for future runs.

    An unusable terminal cannot be prompted, so it degrades to plaintext rather
    than aborting, honouring the "encrypt when possible, never abort" policy.
    """
    status = inspect_token_cache(path=cache_path, env=env)
    if status.state == "encrypted":
        hint = _HINT_LOCKOUT.format(path=cache_path)
        console.message(hint)
        raise TokenCacheError(hint)
    if ack_store is not None and ack_store.is_acknowledged():
        return FileTokenCache(path=cache_path)
    if status.state == "absent":
        console.message(_HINT_FRESH.format(path=cache_path))
    elif status.state == "plaintext":
        console.message(_HINT_LEGACY_PLAINTEXT.format(path=cache_path))
    print(_CONFIRM_WARNING, file=sys.stderr)
    try:
        confirmed = console.confirm(_CONFIRM_PROMPT)
    except OSError:
        # The confirmation warning already disclosed plaintext storage; record
        # it so a later non-interactive build does not repeat the warning.
        globals()["_WARNED"] = True
        return FileTokenCache(path=cache_path)
    if confirmed:
        if ack_store is not None:
            _offer_to_remember(console, ack_store)
        return FileTokenCache(path=cache_path)
    raise TokenCacheError()


def _offer_to_remember(console: ConsoleIO, ack_store: PlaintextAckStore) -> None:
    """Ask whether to persist the plaintext choice, defaulting to yes.

    Accepting records the acknowledgement and prints the saved notice so later
    no-source builds stay silent. An unusable terminal skips persistence and
    proceeds plaintext for this run only.
    """
    try:
        remember = console.confirm(_REMEMBER_PROMPT, default=True)
    except OSError:
        return
    if remember:
        ack_store.remember()
        console.message(_SAVED_NOTICE)


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
