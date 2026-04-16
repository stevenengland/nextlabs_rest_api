from __future__ import annotations

import pytest
import typer

from nextlabs_sdk._cli._client_factory import (
    make_cloudaz_client,
    make_pdp_client,
)
from nextlabs_sdk._cli._context import CliContext


def _make_ctx(
    *,
    base_url: str | None = "https://example.com",
    username: str | None = "user",
    password: str | None = "pass",
    client_id: str = "client",
    client_secret: str | None = "secret",
) -> CliContext:
    return CliContext(
        base_url=base_url,
        username=username,
        password=password,
        client_id=client_id,
        client_secret=client_secret,
        pdp_url=None,
        json_output=False,
        no_verify=False,
        timeout=30.0,
    )


def test_cloudaz_factory_raises_when_base_url_missing() -> None:
    ctx = _make_ctx(base_url=None)
    with pytest.raises(typer.BadParameter, match="base-url"):
        make_cloudaz_client(ctx)


def test_cloudaz_factory_raises_when_username_missing() -> None:
    ctx = _make_ctx(username=None)
    with pytest.raises(typer.BadParameter, match="username"):
        make_cloudaz_client(ctx)


def test_cloudaz_factory_raises_when_password_missing() -> None:
    ctx = _make_ctx(password=None)
    with pytest.raises(typer.BadParameter, match="password"):
        make_cloudaz_client(ctx)


def test_pdp_factory_raises_when_base_url_missing() -> None:
    ctx = _make_ctx(base_url=None)
    with pytest.raises(typer.BadParameter, match="base-url"):
        make_pdp_client(ctx)


def test_pdp_factory_raises_when_client_secret_missing() -> None:
    ctx = _make_ctx(client_secret=None)
    with pytest.raises(typer.BadParameter, match="client-secret"):
        make_pdp_client(ctx)
