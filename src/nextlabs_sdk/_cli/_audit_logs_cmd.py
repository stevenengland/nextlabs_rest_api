from __future__ import annotations

from typing import Annotated

import typer

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, render
from nextlabs_sdk._cloudaz._audit_log_models import AuditLogQuery

audit_logs_app = typer.Typer(help="Entity audit log commands")

_AUDIT_LOG_COLUMNS = (
    ColumnDef("ID", "id"),
    ColumnDef("Timestamp", "timestamp"),
    ColumnDef("Action", "action"),
    ColumnDef("Actor", "actor"),
    ColumnDef("Entity Type", "entity_type"),
    ColumnDef("Entity ID", "entity_id"),
)


@audit_logs_app.command()
@cli_error_handler
def search(
    ctx: typer.Context,
    start_date: Annotated[int, typer.Option(help="Start date (epoch ms)")],
    end_date: Annotated[int, typer.Option(help="End date (epoch ms)")],
    entity_type: Annotated[
        str | None, typer.Option(help="Filter by entity type")
    ] = None,
    action: Annotated[str | None, typer.Option(help="Filter by action")] = None,
    page_size: Annotated[int | None, typer.Option(help="Results per page")] = None,
    sort_by: Annotated[str | None, typer.Option(help="Sort field")] = None,
    sort_order: Annotated[str | None, typer.Option(help="Sort order")] = None,
) -> None:
    """Search entity audit logs."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    query = AuditLogQuery(
        start_date=start_date,
        end_date=end_date,
        entity_type=entity_type,
        action=action,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    entries = list(client.audit_logs.search(query))
    render(cli_ctx, entries, _AUDIT_LOG_COLUMNS, title="Audit Logs")
