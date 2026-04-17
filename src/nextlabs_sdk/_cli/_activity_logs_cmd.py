"""CLI commands for the Reporter activity-logs service."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from nextlabs_sdk import exceptions as sdk_exceptions
from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._binary_output import write_bytes
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, render
from nextlabs_sdk._cli._payload_loader import load_payload
from nextlabs_sdk._cloudaz._activity_log_query_models import ActivityLogQuery

activity_logs_app = typer.Typer(help="Report activity log commands.")

_ENFORCEMENT_COLUMNS = (
    ColumnDef("Row ID", "row_id"),
    ColumnDef("Time", "time"),
    ColumnDef("User", "user_name"),
    ColumnDef("Policy", "policy_name"),
    ColumnDef("Decision", "policy_decision"),
    ColumnDef("Action", "action"),
)

_ATTRIBUTE_COLUMNS = (
    ColumnDef("Name", "name"),
    ColumnDef("Value", "value"),
    ColumnDef("Data Type", "data_type"),
    ColumnDef("Attr Type", "attr_type"),
    ColumnDef("Dynamic", "is_dynamic"),
)


def _load_query(query_path: Path) -> ActivityLogQuery:
    raw = load_payload(query_path)
    try:
        return ActivityLogQuery.model_validate(raw)
    except ValueError as exc:
        raise sdk_exceptions.NextLabsError(
            f"Invalid activity log query in {query_path}: {exc}",
        ) from None


@activity_logs_app.command()
@cli_error_handler
def search(
    ctx: typer.Context,
    query: Annotated[
        Path,
        typer.Option("--query", help="Path to a JSON query file"),
    ],
    page_size: Annotated[
        int, typer.Option("--page-size", help="Entries per page")
    ] = 20,
) -> None:
    """Search activity logs (first page of results)."""
    cli_ctx: CliContext = ctx.obj
    log_query = _load_query(query)
    client = _client_factory.make_cloudaz_client(cli_ctx)
    paginator = client.activity_logs.search(log_query, page_size=page_size)
    page = paginator.first_page()
    render(cli_ctx, page.entries, _ENFORCEMENT_COLUMNS, title="Activity Logs")


@activity_logs_app.command(name="get-by-row-id")
@cli_error_handler
def show_row(
    ctx: typer.Context,
    row_id: Annotated[int, typer.Argument(help="Activity log row ID")],
) -> None:
    """Retrieve the full attribute detail for a single activity log row."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    attributes = client.activity_logs.get_by_row_id(row_id)
    render(cli_ctx, attributes, _ATTRIBUTE_COLUMNS, title=f"Row {row_id}")


@activity_logs_app.command()
@cli_error_handler
def export(
    ctx: typer.Context,
    query: Annotated[
        Path,
        typer.Option("--query", help="Path to a JSON query file"),
    ],
    output: Annotated[
        Path,
        typer.Option("--output", help="Destination file path"),
    ],
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite/--no-overwrite", help="Replace existing file"),
    ] = False,
) -> None:
    """Export matching activity logs as raw bytes to ``--output``."""
    cli_ctx: CliContext = ctx.obj
    log_query = _load_query(query)
    client = _client_factory.make_cloudaz_client(cli_ctx)
    payload = client.activity_logs.export(log_query)
    write_bytes(output, payload, overwrite=overwrite)


@activity_logs_app.command(name="export-by-row-id")
@cli_error_handler
def export_row(
    ctx: typer.Context,
    row_id: Annotated[int, typer.Argument(help="Activity log row ID")],
    output: Annotated[
        Path,
        typer.Option("--output", help="Destination file path"),
    ],
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite/--no-overwrite", help="Replace existing file"),
    ] = False,
) -> None:
    """Export a single activity log row as raw bytes to ``--output``."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    payload = client.activity_logs.export_by_row_id(row_id)
    write_bytes(output, payload, overwrite=overwrite)
