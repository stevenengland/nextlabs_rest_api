from __future__ import annotations

from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._output_format import OutputFormat


def test_cli_context_defaults_to_table_output() -> None:
    ctx = CliContext(
        base_url=None,
        username=None,
        password=None,
        client_id="c",
        client_secret=None,
        pdp_url=None,
        output_format=OutputFormat.TABLE,
        verify=None,
        timeout=30.0,
    )
    assert ctx.output_format is OutputFormat.TABLE


def test_cli_context_accepts_json_output_format() -> None:
    ctx = CliContext(
        base_url=None,
        username=None,
        password=None,
        client_id="c",
        client_secret=None,
        pdp_url=None,
        output_format=OutputFormat.JSON,
        verify=None,
        timeout=30.0,
    )
    assert ctx.output_format is OutputFormat.JSON
