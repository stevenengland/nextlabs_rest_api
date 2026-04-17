from __future__ import annotations

from pathlib import Path

import typer

from nextlabs_sdk._auth._static_token_auth import StaticTokenAuth
from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._config import HttpConfig
from nextlabs_sdk._pdp._client import PdpClient


def _build_file_cache(ctx: CliContext) -> FileTokenCache:
    if ctx.cache_dir:
        return FileTokenCache(path=Path(ctx.cache_dir) / "tokens.json")
    return FileTokenCache()


def _cache_key(ctx: CliContext) -> str:
    return f"{ctx.base_url}/cas/oidc/accessToken|{ctx.username}|{ctx.client_id}"


def _has_valid_cached_token(ctx: CliContext) -> bool:
    if not (ctx.base_url and ctx.username):
        return False
    cache = _build_file_cache(ctx)
    entry = cache.load(_cache_key(ctx))
    return entry is not None and not entry.is_expired()


def make_cloudaz_client(ctx: CliContext) -> CloudAzClient:
    if not ctx.base_url:
        raise typer.BadParameter("--base-url or NEXTLABS_BASE_URL is required")

    config = HttpConfig(
        timeout=ctx.timeout,
        verify_ssl=not ctx.no_verify,
    )

    if ctx.token:
        return CloudAzClient(
            base_url=ctx.base_url,
            client_id=ctx.client_id,
            http_config=config,
            auth=StaticTokenAuth(ctx.token),
        )

    if not ctx.username:
        raise typer.BadParameter("--username or NEXTLABS_USERNAME is required")
    if not ctx.password and not _has_valid_cached_token(ctx):
        raise typer.BadParameter(
            "--password or NEXTLABS_PASSWORD is required "
            "(or run `nextlabs auth login` first)",
        )

    return CloudAzClient(
        base_url=ctx.base_url,
        username=ctx.username,
        password=ctx.password,
        client_id=ctx.client_id,
        http_config=config,
        token_cache=_build_file_cache(ctx),
    )


def make_pdp_client(ctx: CliContext) -> PdpClient:
    if not ctx.base_url:
        raise typer.BadParameter("--base-url or NEXTLABS_BASE_URL is required")
    if not ctx.client_secret:
        raise typer.BadParameter(
            "--client-secret or NEXTLABS_CLIENT_SECRET is required",
        )
    config = HttpConfig(
        timeout=ctx.timeout,
        verify_ssl=not ctx.no_verify,
    )
    return PdpClient(
        base_url=ctx.pdp_url or ctx.base_url,
        client_id=ctx.client_id,
        client_secret=ctx.client_secret,
        http_config=config,
    )
