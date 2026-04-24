from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nextlabs_sdk._auth._active_account._active_account_store import (
    ActiveAccountStore,
)
from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache
from nextlabs_sdk._cli._account_preferences import AccountPreferences
from nextlabs_sdk._cli._account_preferences_store import AccountPreferencesStore
from nextlabs_sdk._cli._context import CliContext


@dataclass(frozen=True)
class ResolvedAccount:
    """Effective account identifiers for a CLI invocation."""

    base_url: str
    username: str
    client_id: str
    kind: str = "cloudaz"


def build_active_store(ctx: CliContext) -> ActiveAccountStore:
    if ctx.cache_dir:
        return ActiveAccountStore(path=Path(ctx.cache_dir) / "active_account.json")
    return ActiveAccountStore()


def build_file_cache(ctx: CliContext) -> FileTokenCache:
    if ctx.cache_dir:
        return FileTokenCache(path=Path(ctx.cache_dir) / "tokens.json")
    return FileTokenCache()


def build_prefs_store(ctx: CliContext) -> AccountPreferencesStore:
    if ctx.cache_dir:
        return AccountPreferencesStore(
            path=Path(ctx.cache_dir) / "account_prefs.json",
        )
    return AccountPreferencesStore()


def prefs_key_for(account: ResolvedAccount) -> str:
    return f"{account.base_url}|{account.username}|{account.client_id}|{account.kind}"


def _legacy_prefs_key_for(account: ResolvedAccount) -> str | None:
    """Legacy 3-segment prefs key for CloudAz accounts (pre-#58)."""
    if account.kind != "cloudaz":
        return None
    return f"{account.base_url}|{account.username}|{account.client_id}"


def load_account_prefs(
    store: AccountPreferencesStore,
    account: ResolvedAccount,
) -> AccountPreferences | None:
    """Load prefs for ``account``, falling back to the legacy 3-segment key.

    Pre-#58 CloudAz installs wrote prefs under a 3-segment key
    (``<base_url>|<username>|<client_id>``). New writes use the 4-segment
    key; this helper lets existing users upgrade without losing their
    persisted ``verify_ssl`` preference.
    """
    entry = store.load(prefs_key_for(account))
    if entry is not None:
        return entry
    legacy = _legacy_prefs_key_for(account)
    if legacy is None:
        return None
    return store.load(legacy)


def effective_verify_ssl(
    store: AccountPreferencesStore,
    account: ResolvedAccount | None,
    ctx_verify: bool | None,
) -> bool:
    """Return the ``verify_ssl`` value the CLI should actually use.

    Precedence — mirrored by both the runtime HTTP config and login
    persistence so the two never disagree:

    1. Explicit CLI flag (``ctx_verify`` / ``--verify`` / ``--no-verify``).
    2. Persisted account preference (written by a previous login).
    3. Default ``True``.

    When login persists its result it must go through this helper so
    a silent re-login (which uses the persisted preference to build
    the HTTP client) does not then overwrite that same preference with
    the default ``True``.
    """
    if ctx_verify is not None:
        return ctx_verify
    if account is None:
        return True
    entry = load_account_prefs(store, account)
    if entry is None:
        return True
    return entry.verify_ssl


def resolve_account(ctx: CliContext) -> ResolvedAccount | None:
    """Resolve the effective account identifiers for ``ctx``.

    Precedence:
    1. Explicit ``base_url`` AND ``username`` from CLI/env.
    2. Active account pointer fills the missing pieces.
    3. ``None`` when nothing is available — caller surfaces guidance.

    When the resolver falls back to the active-account pointer, the
    pointer's ``client_id`` and ``kind`` are used so that non-default
    values chosen at login time keep working without re-passing
    ``--client-id`` on every command. When both ``base_url`` and
    ``username`` are explicit, the resolver returns ``ctx.client_id``
    directly with the default ``kind="cloudaz"`` (explicit CloudAz
    flags never resolve to a PDP account).

    This function does **not** consider ``ctx.token``; callers that honour
    pre-issued tokens should bypass the resolver entirely.
    """
    base_url = ctx.base_url
    username = ctx.username

    if base_url and username:
        return ResolvedAccount(
            base_url=base_url,
            username=username,
            client_id=ctx.client_id,
        )

    pointer = build_active_store(ctx).load()
    if pointer is None:
        return None

    return ResolvedAccount(
        base_url=base_url or pointer.base_url,
        username=username or pointer.username,
        client_id=pointer.client_id,
        kind=pointer.kind,
    )
