"""PDP ``auth login`` flow: collect, mint, persist, activate."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass

import httpx
import typer

from nextlabs_sdk._auth._active_account._active_account import ActiveAccount
from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._cli._account_menu import AccountIdentifier, cache_key_for
from nextlabs_sdk._cli._account_preferences import AccountPreferences
from nextlabs_sdk._cli._account_resolver import (
    build_active_store,
    build_file_cache,
    build_prefs_store,
)
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._output import print_success
from nextlabs_sdk._cli._pdp_auth_source import PdpAuthSource
from nextlabs_sdk._pdp._token_url import resolve_pdp_token_url
from nextlabs_sdk.exceptions import AuthenticationError

_HTTP_OK = 200
_KIND_PDP = "pdp"
_PDP_TOKEN_ENDPOINT = "/dpc/oauth"
_CLOUDAZ_TOKEN_ENDPOINT = "/cas/token"


def login_pdp(cli_ctx: CliContext) -> None:
    """Register a PDP account via OAuth2 client-credentials."""
    flavor = _resolve_flavor(cli_ctx)
    pdp_url = _resolve_pdp_url(cli_ctx, flavor)
    auth_base_url = _resolve_auth_base_url(cli_ctx, flavor)
    client_secret = _resolve_client_secret(cli_ctx, flavor)

    token_url = resolve_pdp_token_url(
        base_url=pdp_url,
        auth_base_url=auth_base_url,
        token_url=None,
    )
    verify_ssl = True if cli_ctx.verify is None else cli_ctx.verify
    payload = _mint_client_credentials_token(
        token_url=token_url,
        client_id=cli_ctx.client_id,
        client_secret=client_secret,
        verify_ssl=verify_ssl,
        timeout=cli_ctx.timeout,
    )

    account = AccountIdentifier(
        base_url=auth_base_url or pdp_url,
        username="",
        client_id=cli_ctx.client_id,
        kind=_KIND_PDP,
    )
    _persist_login(
        cli_ctx,
        _PersistedLogin(
            account=account,
            payload=payload,
            client_secret=client_secret,
            pdp_url=pdp_url,
            flavor=flavor,
            verify_ssl=verify_ssl,
        ),
    )
    print_success("PDP login successful; credentials cached")


def _resolve_flavor(cli_ctx: CliContext) -> PdpAuthSource:
    if cli_ctx.pdp_auth is not None:
        return cli_ctx.pdp_auth
    return PdpAuthSource.CLOUDAZ if cli_ctx.base_url else PdpAuthSource.PDP


def _resolve_pdp_url(cli_ctx: CliContext, flavor: PdpAuthSource) -> str:
    if cli_ctx.pdp_url:
        return cli_ctx.pdp_url
    if sys.stdin.isatty():
        return typer.prompt("PDP base URL")
    suffix = " for --pdp-auth=pdp" if flavor is PdpAuthSource.PDP else ""
    raise typer.BadParameter(
        f"--pdp-url or NEXTLABS_PDP_URL is required{suffix}",
    )


def _resolve_auth_base_url(
    cli_ctx: CliContext,
    flavor: PdpAuthSource,
) -> str | None:
    if flavor is not PdpAuthSource.CLOUDAZ:
        return None
    if cli_ctx.base_url:
        return cli_ctx.base_url
    if sys.stdin.isatty():
        return typer.prompt("CloudAz base URL")
    raise typer.BadParameter(
        "--base-url or NEXTLABS_BASE_URL is required for --pdp-auth=cloudaz",
    )


def _resolve_client_secret(cli_ctx: CliContext, flavor: PdpAuthSource) -> str:
    if cli_ctx.client_secret:
        return cli_ctx.client_secret
    if sys.stdin.isatty():
        return typer.prompt("Client secret", hide_input=True)
    endpoint = (
        _CLOUDAZ_TOKEN_ENDPOINT
        if flavor is PdpAuthSource.CLOUDAZ
        else _PDP_TOKEN_ENDPOINT
    )
    raise typer.BadParameter(
        "--client-secret or NEXTLABS_CLIENT_SECRET is required "
        f"(used at {endpoint})",
    )


@dataclass(frozen=True)
class _TokenPayload:
    access_token: str
    expires_in: int
    token_type: str
    scope: str | None


def _mint_client_credentials_token(
    *,
    token_url: str,
    client_id: str,
    client_secret: str,
    verify_ssl: bool,
    timeout: float,
) -> _TokenPayload:
    response = httpx.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=timeout,
        verify=verify_ssl,
    )
    if response.status_code != _HTTP_OK:
        raise AuthenticationError(
            f"Token acquisition failed: HTTP {response.status_code}",
            status_code=response.status_code,
            response_body=response.text,
            request_method="POST",
            request_url=token_url,
        )
    body = response.json()
    return _TokenPayload(
        access_token=body["access_token"],
        expires_in=int(body["expires_in"]),
        token_type=body.get("token_type", "bearer"),
        scope=body.get("scope"),
    )


@dataclass(frozen=True)
class _PersistedLogin:
    account: AccountIdentifier
    payload: _TokenPayload
    client_secret: str
    pdp_url: str
    flavor: PdpAuthSource
    verify_ssl: bool


def _persist_login(cli_ctx: CliContext, record: _PersistedLogin) -> None:
    cache = build_file_cache(cli_ctx)
    prefs = build_prefs_store(cli_ctx)
    active = build_active_store(cli_ctx)
    account = record.account
    payload = record.payload

    cache.save(
        cache_key_for(account),
        CachedToken(
            access_token=payload.access_token,
            refresh_token=None,
            expires_at=time.time() + payload.expires_in,
            token_type=payload.token_type,
            scope=payload.scope,
            id_token=None,
            refresh_expires_at=None,
            client_secret=record.client_secret,
        ),
    )
    prefs.save(
        _prefs_key(account),
        AccountPreferences(
            verify_ssl=record.verify_ssl,
            pdp_url=record.pdp_url,
            pdp_auth_source=record.flavor.value,
        ),
    )
    active.save(
        ActiveAccount(
            base_url=account.base_url,
            username=account.username,
            client_id=account.client_id,
            kind=account.kind,
        ),
    )


def _prefs_key(account: AccountIdentifier) -> str:
    return f"{account.base_url}|{account.username}|{account.client_id}|{account.kind}"
