from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nextlabs_sdk._auth._active_account._active_account_store import (
    ActiveAccountStore,
)
from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache
from nextlabs_sdk._cli._account_preferences_store import AccountPreferencesStore
from nextlabs_sdk._cli._context import CliContext


@dataclass(frozen=True)
class ResolvedAccount:
    """Effective account identifiers for a CLI invocation."""

    base_url: str
    username: str
    client_id: str


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
    return f"{account.base_url}|{account.username}|{account.client_id}"


def resolve_account(ctx: CliContext) -> ResolvedAccount | None:
    """Resolve the effective account identifiers for ``ctx``.

    Precedence:
    1. Explicit ``base_url`` AND ``username`` from CLI/env.
    2. Active account pointer fills the missing pieces.
    3. ``None`` when nothing is available — caller surfaces guidance.

    When the resolver falls back to the active-account pointer, the
    pointer's ``client_id`` is used so that non-default client IDs chosen
    at login time keep working without re-passing ``--client-id`` on every
    command. When both ``base_url`` and ``username`` are explicit, the
    resolver returns ``ctx.client_id`` directly.

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
    )
