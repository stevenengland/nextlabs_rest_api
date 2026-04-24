from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel
from rich.console import Console

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._binary_output import write_bytes
from nextlabs_sdk._cli._bulk_ids import parse_bulk_ids
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._detail_renderers import register_detail_renderer
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, print_error, render
from nextlabs_sdk._cli._payload_loader import load_payload
from nextlabs_sdk._cli._time_parser import now_epoch_ms, parse_time
from nextlabs_sdk._cloudaz._audit_log_models import (
    AuditLogEntry,
    AuditLogQuery,
    ExportAuditLogsRequest,
)

audit_logs_app = typer.Typer(help="Entity audit log commands")

_AUDIT_LOG_COLUMNS = (
    ColumnDef("ID", "id"),
    ColumnDef("Timestamp", "timestamp"),
    ColumnDef("Action", "action"),
    ColumnDef("Actor", "actor"),
    ColumnDef("Entity Type", "entity_type"),
    ColumnDef("Entity ID", "entity_id"),
)

_AUDIT_LOG_WIDE_COLUMNS: tuple[ColumnDef, ...] = (
    ColumnDef("Actor ID", "actor_id"),
    ColumnDef("Old Value", "old_value"),
    ColumnDef("New Value", "new_value"),
)

_USER_COLUMNS = (
    ColumnDef("Username", "username"),
    ColumnDef("First Name", "first_name"),
    ColumnDef("Last Name", "last_name"),
)


_DATE_HELP = (
    "Accepts epoch milliseconds (e.g. 1737014400000), ISO 8601 datetime "
    "(e.g. 2024-01-15 or 2024-01-15T10:30:00+02:00, naive values treated "
    "as UTC), or a relative offset from now (e.g. 30s, 5m, 2h, 3d, 1w)."
)


@audit_logs_app.command()
@cli_error_handler
def search(  # noqa: WPS211
    ctx: typer.Context,
    start_date: Annotated[str, typer.Option(help=f"Start date. {_DATE_HELP}")],
    end_date: Annotated[
        str | None,
        typer.Option(help=f"End date (defaults to now). {_DATE_HELP}"),
    ] = None,
    entity_type: Annotated[
        str | None, typer.Option(help="Filter by entity type")
    ] = None,
    action: Annotated[str | None, typer.Option(help="Filter by action")] = None,
    page_size: Annotated[int, typer.Option(help="Results per page")] = 20,
    sort_by: Annotated[str, typer.Option(help="Sort field")] = "timestamp",
    sort_order: Annotated[str, typer.Option(help="Sort order")] = "DESC",
) -> None:
    """Search entity audit logs.

    ``--sort-by``, ``--sort-order``, and ``--page-size`` default to values
    accepted by live reporter deployments. The server rejects requests that
    omit these fields (observed 400/500 responses) even though the OpenAPI
    spec marks them optional.
    """
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    start_ms = parse_time(start_date)
    end_ms = now_epoch_ms() if end_date is None else parse_time(end_date)
    query = AuditLogQuery(
        start_date=start_ms,
        end_date=end_ms,
        entity_type=entity_type,
        action=action,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    entries = list(client.audit_logs.search(query))
    render(
        cli_ctx,
        entries,
        _AUDIT_LOG_COLUMNS,
        title="Audit Logs",
        wide_columns=_AUDIT_LOG_WIDE_COLUMNS,
    )


@audit_logs_app.command()
@cli_error_handler
def export(  # noqa: WPS211
    ctx: typer.Context,
    output: Annotated[
        Path,
        typer.Option("--output", help="Destination file path"),
    ],
    query_path: Annotated[
        Path | None,
        typer.Option(
            "--query",
            help=(
                "Path to a JSON AuditLogQuery payload. Live reporter servers "
                "require 'sortBy', 'sortOrder', and 'pageSize' to be present "
                "in the payload."
            ),
        ),
    ] = None,
    ids: Annotated[
        list[int] | None,
        typer.Option("--id", help="Audit log entry ID (repeatable)"),
    ] = None,
    ids_csv: Annotated[
        str | None,
        typer.Option("--ids", help="Comma-separated audit log entry IDs"),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite/--no-overwrite", help="Replace existing file"),
    ] = False,
) -> None:
    """Export audit logs as bytes to ``--output``.

    The ``--query`` JSON file is forwarded verbatim; live reporter servers
    reject queries missing ``sortBy``, ``sortOrder``, or ``pageSize``, so
    include those fields in the payload.
    """
    resolved_ids: list[int] | None = None
    if ids or ids_csv:
        resolved_ids = parse_bulk_ids(ids, ids_csv)
    query: AuditLogQuery | None = None
    if query_path is not None:
        query = AuditLogQuery.model_validate(load_payload(query_path))
    if resolved_ids is None and query is None:
        print_error("Provide --query PATH and/or --id/--ids")
        raise typer.Exit(code=1)
    request = ExportAuditLogsRequest(ids=resolved_ids, query=query)
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    payload = client.audit_logs.export(request)
    write_bytes(output, payload, overwrite=overwrite)


@audit_logs_app.command(name="list-users")
@cli_error_handler
def list_users(ctx: typer.Context) -> None:
    """List users that appear in audit log records."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    users = client.audit_logs.list_users()
    render(cli_ctx, users, _USER_COLUMNS, title="Audit Log Users")


def _render_audit_entry_detail(model: BaseModel, console: Console) -> None:
    assert isinstance(model, AuditLogEntry)
    console.print(f"[bold]AuditLogEntry[/bold] {model.id}")
    console.print(f"  [bold]Timestamp[/bold]:   {model.timestamp}")
    console.print(f"  [bold]Action[/bold]:      {model.action}")
    console.print(f"  [bold]Actor[/bold]:       {model.actor} (id={model.actor_id})")
    console.print(f"  [bold]Entity Type[/bold]: {model.entity_type}")
    console.print(f"  [bold]Entity ID[/bold]:   {model.entity_id}")
    console.print(f"  [bold]Old Value[/bold]:   {model.old_value}")
    console.print(f"  [bold]New Value[/bold]:   {model.new_value}")


register_detail_renderer(AuditLogEntry, _render_audit_entry_detail)
