from __future__ import annotations

import sys
import time
from dataclasses import dataclass

import typer

from nextlabs_sdk._auth._refresh_token_policy import RefreshDecision, decide
from nextlabs_sdk._auth._static_token_auth import StaticTokenAuth
from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache
from nextlabs_sdk._cli._account_resolver import (
    ResolvedAccount,
    build_file_cache,
    build_prefs_store,
    effective_verify_ssl,
    load_account_prefs,
    resolve_account,
)
from nextlabs_sdk._cli._cache_key import cache_key_for
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._pdp_auth_source import PdpAuthSource
from nextlabs_sdk._cli._pdp_client_id import resolve_pdp_client_id
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._config import HttpConfig
from nextlabs_sdk._pdp._client import PdpClient

_LOGIN_HINT = "run `nextlabs auth login` or `nextlabs auth use`"
_BASE_URL_REQUIRED = f"--base-url is required (or {_LOGIN_HINT})"
_USERNAME_REQUIRED = f"--username is required (or {_LOGIN_HINT})"
_PASSWORD_REQUIRED = f"--password or NEXTLABS_PASSWORD is required (or {_LOGIN_HINT})"

_PDP_URL_HELP = "PDP API host serving /dpc/authorization/*"
_CLOUDAZ_ENDPOINT = "/cas/token on the CloudAz host"
_PDP_ENDPOINT = "/dpc/oauth on the PDP host"
_ACTIVE_IS_PDP = (
    "Active account is a PDP account; CloudAz commands need a CloudAz account. "
    "Run `nextlabs auth use <username>@<url>` to switch, or pass --base-url and "
    "--username explicitly."
)


def _client_secret_required(flavor: PdpAuthSource) -> str:
    endpoint = _CLOUDAZ_ENDPOINT if flavor is PdpAuthSource.CLOUDAZ else _PDP_ENDPOINT
    return (
        "--client-secret or NEXTLABS_CLIENT_SECRET is required " f"(used at {endpoint})"
    )


def _base_url_required_for_cloudaz_flavor() -> str:
    return (
        "--base-url or NEXTLABS_BASE_URL is required for --pdp-auth=cloudaz "
        f"(authenticates at {_CLOUDAZ_ENDPOINT})"
    )


def _pdp_url_required(flavor: PdpAuthSource) -> str:
    if flavor is PdpAuthSource.PDP:
        return (
            "--pdp-url or NEXTLABS_PDP_URL is required for --pdp-auth=pdp "
            f"(authenticates at {_PDP_ENDPOINT})"
        )
    return f"--pdp-url or NEXTLABS_PDP_URL is required ({_PDP_URL_HELP})"


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


def _prompt_url_if_tty(label: str) -> str | None:
    if not sys.stdin.isatty():
        return None
    return typer.prompt(label)


def _http_config(ctx: CliContext, account: ResolvedAccount | None) -> HttpConfig:
    return HttpConfig(
        timeout=ctx.timeout,
        verify_ssl=effective_verify_ssl(build_prefs_store(ctx), account, ctx.verify),
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
        if account.kind != "cloudaz":
            raise typer.BadParameter(_ACTIVE_IS_PDP)
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
    overrides = _load_pdp_overrides(ctx, account)
    flavor = _resolve_flavor(ctx, overrides)
    base_url = _resolve_cloudaz_base_url(ctx, account, flavor)
    pdp_url = _resolve_pdp_url(ctx, flavor, overrides)
    client_secret = _resolve_client_secret(ctx, flavor, overrides)
    client_id = _resolve_pdp_client_id(ctx, account, flavor)

    auth_base_url = base_url if flavor is PdpAuthSource.CLOUDAZ else None

    return PdpClient(
        base_url=pdp_url,
        auth_base_url=auth_base_url,
        client_id=client_id,
        client_secret=client_secret,
        http_config=_http_config(ctx, account),
    )


def _resolve_pdp_client_id(
    ctx: CliContext,
    account: ResolvedAccount | None,
    flavor: PdpAuthSource,
) -> str:
    if ctx.pdp_client_id:
        return ctx.pdp_client_id
    if account is not None:
        return account.client_id
    return resolve_pdp_client_id(ctx, flavor)


@dataclass(frozen=True)
class _PdpOverrides:
    """Cached PDP credentials pulled from active-account storage."""

    client_secret: str | None = None
    pdp_url: str | None = None
    flavor: PdpAuthSource | None = None


def _load_pdp_overrides(
    ctx: CliContext,
    account: ResolvedAccount | None,
) -> _PdpOverrides:
    if account is None or account.kind != "pdp":
        return _PdpOverrides()
    prefs = load_account_prefs(build_prefs_store(ctx), account)
    entry = build_file_cache(ctx).load(cache_key_for(account))
    flavor = _coerce_flavor(prefs.pdp_auth_source if prefs else None)
    return _PdpOverrides(
        client_secret=entry.client_secret if entry else None,
        pdp_url=prefs.pdp_url if prefs else None,
        flavor=flavor,
    )


def _coerce_flavor(raw: str | None) -> PdpAuthSource | None:
    if raw is None:
        return None
    try:
        return PdpAuthSource(raw)
    except ValueError:
        return None


def _resolve_flavor(
    ctx: CliContext,
    overrides: _PdpOverrides,
) -> PdpAuthSource:
    if ctx.pdp_auth is not None:
        return ctx.pdp_auth
    if overrides.flavor is not None:
        return overrides.flavor
    return PdpAuthSource.CLOUDAZ if ctx.base_url else PdpAuthSource.PDP


def _resolve_cloudaz_base_url(
    ctx: CliContext,
    account: ResolvedAccount | None,
    flavor: PdpAuthSource,
) -> str | None:
    if flavor is not PdpAuthSource.CLOUDAZ:
        return None
    account_base_url = account.base_url if account else None
    base_url = ctx.base_url or account_base_url
    if base_url:
        return base_url
    prompted = _prompt_url_if_tty("CloudAz base URL")
    if prompted:
        return prompted
    raise typer.BadParameter(_base_url_required_for_cloudaz_flavor())


def _resolve_pdp_url(
    ctx: CliContext,
    flavor: PdpAuthSource,
    overrides: _PdpOverrides,
) -> str:
    if ctx.pdp_url:
        return ctx.pdp_url
    if overrides.pdp_url:
        return overrides.pdp_url
    prompted = _prompt_url_if_tty("PDP base URL")
    if prompted:
        return prompted
    raise typer.BadParameter(_pdp_url_required(flavor))


def _resolve_client_secret(
    ctx: CliContext,
    flavor: PdpAuthSource,
    overrides: _PdpOverrides,
) -> str:
    if ctx.client_secret:
        return ctx.client_secret
    if overrides.client_secret:
        return overrides.client_secret
    raise typer.BadParameter(_client_secret_required(flavor))
