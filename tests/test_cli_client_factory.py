from __future__ import annotations

import pytest
import typer

from nextlabs_sdk._cli._client_factory import make_cloudaz_client, make_pdp_client
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


@pytest.mark.parametrize(
    "factory,kwargs,match",
    [
        pytest.param(
            make_cloudaz_client, {"base_url": None}, "base-url", id="cloudaz-base-url"
        ),
        pytest.param(
            make_cloudaz_client, {"username": None}, "username", id="cloudaz-username"
        ),
        pytest.param(
            make_cloudaz_client, {"password": None}, "password", id="cloudaz-password"
        ),
        pytest.param(
            make_pdp_client, {"base_url": None}, "base-url", id="pdp-base-url"
        ),
        pytest.param(
            make_pdp_client,
            {"client_secret": None},
            "client-secret",
            id="pdp-client-secret",
        ),
    ],
)
def test_factory_raises_when_required_field_missing(factory, kwargs, match):
    with pytest.raises(typer.BadParameter, match=match):
        factory(_make_ctx(**kwargs))
