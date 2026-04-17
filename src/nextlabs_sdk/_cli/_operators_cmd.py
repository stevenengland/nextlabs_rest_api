"""CLI commands for the CloudAz Operators (data-type) endpoints."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.console import Console

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, render
from nextlabs_sdk._cli._output_format import OutputFormat

operators_app = typer.Typer(help="Operator (data-type) metadata commands.")

_OPERATOR_COLUMNS = (
    ColumnDef("ID", "id"),
    ColumnDef("Key", "key"),
    ColumnDef("Label", "label"),
    ColumnDef("Data Type", "data_type"),
)


@operators_app.command(name="list")
@cli_error_handler
def list_all(ctx: typer.Context) -> None:
    """List every operator across all data types."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    operators = client.operators.list_all()
    render(cli_ctx, operators, _OPERATOR_COLUMNS, title="Operators")


@operators_app.command(name="list-by-type")
@cli_error_handler
def list_by_type(
    ctx: typer.Context,
    data_type: Annotated[str, typer.Argument(help="Data type key, e.g. 'string'")],
) -> None:
    """List operators scoped to a single data type."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    operators = client.operators.list_by_type(data_type)
    render(cli_ctx, operators, _OPERATOR_COLUMNS, title=f"Operators ({data_type})")


@operators_app.command(name="list-types")
@cli_error_handler
def list_types(ctx: typer.Context) -> None:
    """List available data-type keys."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    types = client.operators.list_types()

    if cli_ctx.output_format is OutputFormat.JSON:
        print(json.dumps(types, indent=2))
        return

    console = Console()
    for data_type in types:
        console.print(data_type)
