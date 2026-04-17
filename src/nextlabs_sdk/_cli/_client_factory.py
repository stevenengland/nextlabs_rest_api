from __future__ import annotations

import typer

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
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._config import HttpConfig
from nextlabs_sdk._pdp._client import PdpClient

_LOGIN_HINT = "run `nextlabs auth login` or `nextlabs auth use`"
_BASE_URL_REQUIRED = f"--base-url is required (or {_LOGIN_HINT})"
_USERNAME_REQUIRED = f"--username is required (or {_LOGIN_HINT})"
_PASSWORD_REQUIRED = f"--password or NEXTLABS_PASSWORD is required (or {_LOGIN_HINT})"
_CLIENT_SECRET_REQUIRED = "--client-secret or NEXTLABS_CLIENT_SECRET is required"


def _has_valid_cached_token_for(
    cache: FileTokenCache,
    account: ResolvedAccount,
) -> bool:
    key = (
        f"{account.base_url}/cas/oidc/accessToken"
        f"|{account.username}|{account.client_id}"
    )
    entry = cache.load(key)
    return entry is not None and not entry.is_expired()


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
    if not ctx.password and not _has_valid_cached_token_for(cache, account):
        raise typer.BadParameter(_PASSWORD_REQUIRED)

    return CloudAzClient(
        base_url=account.base_url,
        username=account.username,
        password=ctx.password,
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
