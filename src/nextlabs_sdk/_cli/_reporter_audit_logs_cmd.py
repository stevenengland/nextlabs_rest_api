"""CLI commands for Reporter audit logs."""

from __future__ import annotations

from typing import Annotated

import typer

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, render

reporter_audit_logs_app = typer.Typer(help="Reporter audit log commands.")

_COLUMNS = (
    ColumnDef("ID", "id"),
    ColumnDef("Component", "component"),
    ColumnDef("Owner", "owner_display_name"),
    ColumnDef("Message", "activity_msg"),
    ColumnDef("Created", "created_date"),
)


@reporter_audit_logs_app.command()
@cli_error_handler
def search(
    ctx: typer.Context,
    page_size: Annotated[
        int,
        typer.Option("--page-size", help="Entries per page"),
    ] = 20,
) -> None:
    """Search Reporter audit logs (first page of results)."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    paginator = client.reporter_audit_logs.search(page_size=page_size)
    page = paginator.first_page()
    render(cli_ctx, page.entries, _COLUMNS, title="Reporter Audit Logs")
