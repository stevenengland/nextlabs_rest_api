from __future__ import annotations

import sys
import time

import typer

from nextlabs_sdk._auth._refresh_token_policy import RefreshDecision, decide
from nextlabs_sdk._auth._static_token_auth import StaticTokenAuth
from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache
from nextlabs_sdk._cli._account_preferences_store import AccountPreferencesStore
from nextlabs_sdk._cli._account_resolver import (
    ResolvedAccount,
    build_file_cache,
    build_prefs_store,
    prefs_key_for,
    resolve_account,
)
from nextlabs_sdk._cli._cache_key import cache_key_for
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._config import HttpConfig
from nextlabs_sdk._pdp._client import PdpClient

_LOGIN_HINT = "run `nextlabs auth login` or `nextlabs auth use`"
_BASE_URL_REQUIRED = f"--base-url is required (or {_LOGIN_HINT})"
_USERNAME_REQUIRED = f"--username is required (or {_LOGIN_HINT})"
_PASSWORD_REQUIRED = f"--password or NEXTLABS_PASSWORD is required (or {_LOGIN_HINT})"
_CLIENT_SECRET_REQUIRED = "--client-secret or NEXTLABS_CLIENT_SECRET is required"


def _cached_credentials_usable(
    cache: FileTokenCache,
    account: ResolvedAccount,
    *,
    now: float | None = None,
) -> bool:
    """Return True when the cache holds a credential that avoids a password.

    Either the access token is still fresh, or a refresh token is present
    and not known to be past its lifetime — in which case ``CloudAzAuth``
    can redeem it silently on the next request.
    """
    entry = cache.load(cache_key_for(account))
    if entry is None:
        return False
    effective_now = time.time() if now is None else now
    if not entry.is_expired(now=effective_now):
        return True
    return (
        decide(
            refresh_token=entry.refresh_token,
            refresh_expires_at=entry.refresh_expires_at,
            now=effective_now,
        )
        is RefreshDecision.USE_REFRESH
    )


def _prompt_password_if_tty(account: ResolvedAccount) -> str | None:
    if not sys.stdin.isatty():
        return None
    return typer.prompt(
        f"Password for {account.username}@{account.base_url}",
        hide_input=True,
    )


def _persisted_verify(
    prefs: AccountPreferencesStore,
    account: ResolvedAccount,
) -> bool | None:
    entry = prefs.load(prefs_key_for(account))
    return None if entry is None else entry.verify_ssl


def _effective_verify_ssl(
    ctx: CliContext,
    account: ResolvedAccount | None,
) -> bool:
    if ctx.verify is not None:
        return ctx.verify
    if account is not None:
        persisted = _persisted_verify(build_prefs_store(ctx), account)
        if persisted is not None:
            return persisted
    return True


def _http_config(ctx: CliContext, account: ResolvedAccount | None) -> HttpConfig:
    return HttpConfig(
        timeout=ctx.timeout,
        verify_ssl=_effective_verify_ssl(ctx, account),
        verbose=ctx.verbose,
    )


def _build_static_token_client(ctx: CliContext) -> CloudAzClient:
    if not ctx.base_url:
        raise typer.BadParameter(_BASE_URL_REQUIRED)
    return CloudAzClient(
        base_url=ctx.base_url,
        client_id=ctx.client_id,
        http_config=_http_config(ctx, None),
        auth=StaticTokenAuth(ctx.token or ""),
    )


def _resolve_or_raise(ctx: CliContext) -> ResolvedAccount:
    account = resolve_account(ctx)
    if account is not None:
        return account
    if not ctx.base_url:
        raise typer.BadParameter(_BASE_URL_REQUIRED)
    raise typer.BadParameter(_USERNAME_REQUIRED)


def make_cloudaz_client(ctx: CliContext) -> CloudAzClient:
    if ctx.token:
        return _build_static_token_client(ctx)

    account = _resolve_or_raise(ctx)
    cache = build_file_cache(ctx)

    password = ctx.password or None
    if password is None and not _cached_credentials_usable(cache, account):
        password = _prompt_password_if_tty(account)
        if password is None:
            raise typer.BadParameter(_PASSWORD_REQUIRED)

    return CloudAzClient(
        base_url=account.base_url,
        username=account.username,
        password=password,
        client_id=account.client_id,
        http_config=_http_config(ctx, account),
        token_cache=cache,
    )


def make_pdp_client(ctx: CliContext) -> PdpClient:
    account = resolve_account(ctx)
    fallback_base_url = account.base_url if account else None
    base_url = ctx.base_url or fallback_base_url
    client_id = account.client_id if account else ctx.client_id

    if not base_url:
        raise typer.BadParameter(_BASE_URL_REQUIRED)
    if not ctx.client_secret:
        raise typer.BadParameter(_CLIENT_SECRET_REQUIRED)

    return PdpClient(
        base_url=ctx.pdp_url or base_url,
        client_id=client_id,
        client_secret=ctx.client_secret,
        http_config=_http_config(ctx, account),
    )
