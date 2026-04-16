from __future__ import annotations

import sys
from typing import Annotated

import typer

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, print_success, render, render_json
from nextlabs_sdk._cli._parsing import parse_json_payload
from nextlabs_sdk._cloudaz._report_models import (
    DeleteReportsRequest,
    PolicyActivityReportRequest,
)

reports_app = typer.Typer(help="Report management commands")

_REPORT_COLUMNS = (
    ColumnDef("ID", "id"),
    ColumnDef("Title", "title"),
    ColumnDef("Decision", "decision"),
    ColumnDef("Date Mode", "date_mode"),
    ColumnDef("Type", "type"),
    ColumnDef("Last Updated", "last_updated_date"),
)

_ENFORCEMENT_COLUMNS = (
    ColumnDef("Row ID", "row_id"),
    ColumnDef("Time", "time"),
    ColumnDef("User", "user_name"),
    ColumnDef("Resource", "from_resource_name"),
    ColumnDef("Policy", "policy_name"),
    ColumnDef("Decision", "policy_decision"),
    ColumnDef("Action", "action"),
)


@reports_app.command(name="list")
@cli_error_handler
def list_reports(
    ctx: typer.Context,
    title: Annotated[str, typer.Option(help="Filter by title")] = "",
    shared: Annotated[bool, typer.Option(help="Include shared reports")] = True,
    decision: Annotated[str, typer.Option(help="Policy decision filter")] = "AD",
    sort_by: Annotated[str, typer.Option(help="Sort field")] = "title",
    sort_order: Annotated[str, typer.Option(help="Sort order")] = "ascending",
    page_size: Annotated[int, typer.Option(help="Results per page")] = 20,
) -> None:
    """List saved reports."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    reports = list(
        client.reports.list(
            title=title,
            is_shared=shared,
            policy_decision=decision,
            sort_by=sort_by,
            sort_order=sort_order,
            page_size=page_size,
        )
    )
    render(cli_ctx, reports, _REPORT_COLUMNS, title="Reports")


@reports_app.command()
@cli_error_handler
def get(
    ctx: typer.Context,
    report_id: Annotated[int, typer.Argument(help="Report ID")],
) -> None:
    """Get report detail by ID."""
    client = _client_factory.make_cloudaz_client(ctx.obj)
    detail = client.reports.get(report_id)
    render_json(detail)


@reports_app.command()
@cli_error_handler
def create(
    ctx: typer.Context,
    raw_body: Annotated[str, typer.Option("--data", help="JSON payload")],
) -> None:
    """Create a report from a JSON payload."""
    payload = parse_json_payload(raw_body)
    client = _client_factory.make_cloudaz_client(ctx.obj)
    request = PolicyActivityReportRequest.model_validate(payload)
    report = client.reports.create(request)
    print_success(f"Created report with ID {report.id}")


@reports_app.command()
@cli_error_handler
def modify(
    ctx: typer.Context,
    report_id: Annotated[int, typer.Argument(help="Report ID")],
    raw_body: Annotated[str, typer.Option("--data", help="JSON payload")],
) -> None:
    """Modify a report."""
    payload = parse_json_payload(raw_body)
    client = _client_factory.make_cloudaz_client(ctx.obj)
    request = PolicyActivityReportRequest.model_validate(payload)
    client.reports.modify(report_id, request)
    print_success(f"Modified report {report_id}")


@reports_app.command()
@cli_error_handler
def delete(
    ctx: typer.Context,
    report_ids: Annotated[list[int], typer.Argument(help="Report ID(s) to delete")],
) -> None:
    """Delete reports by ID(s)."""
    client = _client_factory.make_cloudaz_client(ctx.obj)
    request = DeleteReportsRequest(report_ids=report_ids)
    client.reports.delete(request)
    print_success(f"Deleted {len(report_ids)} report(s)")


@reports_app.command()
@cli_error_handler
def widgets(
    ctx: typer.Context,
    report_id: Annotated[int, typer.Argument(help="Report ID")],
) -> None:
    """Get report widget data."""
    client = _client_factory.make_cloudaz_client(ctx.obj)
    widget_data = client.reports.get_widgets(report_id)
    render_json(widget_data)


@reports_app.command()
@cli_error_handler
def enforcements(
    ctx: typer.Context,
    report_id: Annotated[int, typer.Argument(help="Report ID")],
    sort_by: Annotated[str, typer.Option(help="Sort field")] = "rowId",
    sort_order: Annotated[str, typer.Option(help="Sort order")] = "ascending",
    page_size: Annotated[int, typer.Option(help="Results per page")] = 20,
) -> None:
    """Get enforcement logs for a report."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    entries = list(
        client.reports.get_enforcements(
            report_id,
            sort_by=sort_by,
            sort_order=sort_order,
            page_size=page_size,
        )
    )
    render(cli_ctx, entries, _ENFORCEMENT_COLUMNS, title="Enforcements")


@reports_app.command(name="export")
@cli_error_handler
def export_report(
    ctx: typer.Context,
    report_id: Annotated[int, typer.Argument(help="Report ID")],
    sort_by: Annotated[str, typer.Option(help="Sort field")] = "rowId",
    sort_order: Annotated[str, typer.Option(help="Sort order")] = "ascending",
) -> None:
    """Export report data to stdout."""
    client = _client_factory.make_cloudaz_client(ctx.obj)
    exported = client.reports.export(
        report_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    sys.stdout.buffer.write(exported)
