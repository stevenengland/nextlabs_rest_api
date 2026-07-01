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

    Non-interactive sources are consulted in order: ``NEXTLABS_MASTER_PASSWORD``
    then the OS keyring. On a TTY with no such source the remembered plaintext
    choice is honoured first — a remembered choice returns a plaintext cache
    silently, never prompting — and only otherwise is the caller offered an
    interactive passphrase (encrypting on any non-empty entry). An empty entry
    falls through to a plaintext confirmation gate; declining raises
    :class:`TokenCacheError` without writing anything. With no source and no TTY
    the cache falls back to plaintext and emits a single process-wide warning to
    stderr; it never aborts. Setting ``NEXTLABS_DISABLE_TOKEN_ENCRYPTION=1``
    silences that non-interactive warning.

    The remembered choice is consulted only when no non-interactive source
    resolves, so configuring a passphrase later upgrades to encryption without
    resetting the remembered choice. It is checked after the lockout guard, so
    acknowledging plaintext never clobbers an existing encrypted cache.
    """
    console = console or ConsoleIO()
    resolver = PassphraseResolver(
        sources=(
            EnvVarPassphraseSource(),
            KeyringPassphraseSource(),
        )
    )
    material, _label = resolver.resolve(env)
    cache_path = _default_path() if path is None else Path(path)

    if material is not None:
        return EncryptedFileTokenCache(path=cache_path, kek_source=material)

    if console.isatty():
        return _resolve_on_tty(console, cache_path, env, ack_store)

    _abort_if_locked_out(console, cache_path, env)
    _warn_plaintext_once(env)
    return FileTokenCache(path=cache_path)


def _resolve_on_tty(
    console: ConsoleIO,
    cache_path: Path,
    env: Mapping[str, str],
    ack_store: PlaintextAckStore | None,
) -> TokenCache:
    """Resolve the cache on a usable terminal, encrypting when possible.

    The remembered plaintext choice is consulted *before* the interactive
    passphrase prompt, so acknowledging plaintext genuinely stops the CLI from
    asking again — the prompt never fires for a remembered choice. The lockout
    guard still runs first, so a remembered choice can never clobber an existing
    encrypted cache. With no remembered choice the caller is offered a passphrase
    (encrypting on any non-empty entry) and only an empty entry falls through to
    the plaintext confirmation gate.
    """
    status = _abort_if_locked_out(console, cache_path, env)
    if ack_store is not None and ack_store.is_acknowledged():
        return FileTokenCache(path=cache_path)
    material = InteractivePassphraseSource(console).resolve(env)
    if material is not None:
        return EncryptedFileTokenCache(path=cache_path, kek_source=material)
    return _confirm_plaintext_or_abort(console, cache_path, status, ack_store, env)


def _abort_if_locked_out(
    console: ConsoleIO, cache_path: Path, env: Mapping[str, str]
) -> CacheStatus:
    """Raise if ``cache_path`` holds an encrypted cache no source can unlock.

    Shared by both the interactive and non-interactive branches of
    :func:`build_token_cache` so the lockout guarantee ("never fall back to
    plaintext for that file") holds regardless of ``console.isatty()``.
    Returns the inspected status so the interactive caller, which needs it for
    its other hints, does not inspect the file twice.
    """
    status = inspect_token_cache(path=cache_path, env=env)
    if status.state == "encrypted":
        hint = _HINT_LOCKOUT.format(path=cache_path)
        console.message(hint)
        raise TokenCacheError(hint)
    return status


def _confirm_plaintext_or_abort(
    console: ConsoleIO,
    cache_path: Path,
    status: CacheStatus,
    ack_store: PlaintextAckStore | None,
    env: Mapping[str, str],
) -> TokenCache:
    """Gate plaintext storage behind a confirmation on the controlling terminal.

    Emits a state-aware hint first: a first-time hint for an absent cache and a
    plaintext-exposure hint for an existing unencrypted one. The hint already
    discloses that storage is unencrypted and how to encrypt later, so no
    separate stderr warning is emitted here — it would only duplicate the hint.

    Reached only from :func:`_resolve_on_tty`, after the lockout guard, the
    remembered-choice short-circuit, and an empty interactive passphrase entry.
    On confirmation the caller is offered a one-time prompt to remember the
    choice for future runs.

    An unusable terminal cannot be prompted, so it degrades to plaintext rather
    than aborting, honouring the "encrypt when possible, never abort" policy; the
    degradation emits the one-time plaintext warning to stderr so the disclosure
    survives even when the tty hint could not be written.
    """
    if status.state == "absent":
        console.message(_HINT_FRESH.format(path=cache_path))
    elif status.state == "plaintext":
        console.message(_HINT_LEGACY_PLAINTEXT.format(path=cache_path))
    try:
        confirmed = console.confirm(_CONFIRM_PROMPT)
    except OSError:
        _warn_plaintext_once(env)
        return FileTokenCache(path=cache_path)
    if confirmed:
        if ack_store is not None:
            _offer_to_remember(console, ack_store)
        return FileTokenCache(path=cache_path)
    raise TokenCacheError()


def _offer_to_remember(console: ConsoleIO, ack_store: PlaintextAckStore) -> None:
    """Ask whether to persist the plaintext choice, defaulting to yes.

    Accepting records the acknowledgement and prints the saved notice so later
    no-source builds stay silent. An unusable terminal or a failed preferences
    write skips persistence and proceeds plaintext for this run only, so a
    best-effort convenience never aborts an otherwise-successful build.
    """
    try:
        remember = console.confirm(_REMEMBER_PROMPT, default=True)
    except OSError:
        return
    if not remember:
        return
    try:
        ack_store.remember()
    except OSError:
        return
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
