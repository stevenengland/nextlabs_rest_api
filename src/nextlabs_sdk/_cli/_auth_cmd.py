from __future__ import annotations

import typer

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import print_success

auth_app = typer.Typer(help="Authentication commands")


@auth_app.command(name="test")
@cli_error_handler
def test_auth(ctx: typer.Context) -> None:
    """Test CloudAz authentication credentials."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.operators.list_types()
    print_success("Authentication successful")
