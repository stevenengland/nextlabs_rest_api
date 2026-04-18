"""CLI commands for the Reporter system configuration endpoint."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output_format import OutputFormat

system_config_app = typer.Typer(help="Reporter system configuration commands.")


@system_config_app.command()
@cli_error_handler
def get(ctx: typer.Context) -> None:
    """Retrieve Reporter UI configuration settings."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    config = client.system_config.get()

    if cli_ctx.output_format is OutputFormat.JSON:
        print(json.dumps(config.settings, indent=2))
        return

    table = Table(title="System Configuration")
    table.add_column("Key", overflow="fold", no_wrap=False)
    table.add_column("Value", overflow="fold", no_wrap=False)
    for key, entry in sorted(config.settings.items()):
        table.add_row(key, entry)
    Console().print(table)
