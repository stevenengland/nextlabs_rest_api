from __future__ import annotations

from mockito import spy2, verify

from nextlabs_sdk._cli import _account_resolver as ar
from nextlabs_sdk._cli._client_factory import make_cloudaz_client
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._output_format import OutputFormat


def _ctx() -> CliContext:
    return CliContext(
        base_url="https://x",
        username=None,
        password=None,
        client_id="ControlCenterOIDCClient",
        client_secret=None,
        pdp_url=None,
        output_format=OutputFormat.TABLE,
        verify=None,
        timeout=30.0,
        token="abc",
    )


def test_token_bypasses_cache_factory() -> None:
    spy2(ar.build_token_cache)
    make_cloudaz_client(_ctx())
    verify(ar, times=0).build_token_cache(...)
