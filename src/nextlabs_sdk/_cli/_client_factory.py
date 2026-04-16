from __future__ import annotations

import typer

from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._config import HttpConfig
from nextlabs_sdk._pdp._client import PdpClient


def make_cloudaz_client(ctx: CliContext) -> CloudAzClient:
    if not ctx.base_url:
        raise typer.BadParameter("--base-url or NEXTLABS_BASE_URL is required")
    if not ctx.username:
        raise typer.BadParameter("--username or NEXTLABS_USERNAME is required")
    if not ctx.password:
        raise typer.BadParameter("--password or NEXTLABS_PASSWORD is required")
    config = HttpConfig(
        timeout=ctx.timeout,
        verify_ssl=not ctx.no_verify,
    )
    return CloudAzClient(
        base_url=ctx.base_url,
        username=ctx.username,
        password=ctx.password,
        client_id=ctx.client_id,
        http_config=config,
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
