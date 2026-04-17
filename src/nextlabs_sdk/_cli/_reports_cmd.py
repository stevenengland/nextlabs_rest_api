from __future__ import annotations

import sys
from typing import Annotated

import typer
from pydantic import BaseModel
from rich.console import Console

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._detail_renderers import register_detail_renderer
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, print_success, render
from nextlabs_sdk._cli._parsing import parse_json_payload
from nextlabs_sdk._cloudaz._report_models import (
    DeleteReportsRequest,
    PolicyActivityReportDetail,
    PolicyActivityReportRequest,
    WidgetData,
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

_REPORT_DETAIL_COLUMNS = (
    ColumnDef("Criteria", "criteria"),
    ColumnDef("Widgets", "widgets"),
)

_WIDGET_DATA_COLUMNS = (ColumnDef("Enforcements", "enforcements"),)


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
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    detail = client.reports.get(report_id)
    render(cli_ctx, detail, _REPORT_DETAIL_COLUMNS)


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
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    widget_data = client.reports.get_widgets(report_id)
    render(cli_ctx, widget_data, _WIDGET_DATA_COLUMNS)


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


def _render_report_detail(model: BaseModel, console: Console) -> None:
    assert isinstance(model, PolicyActivityReportDetail)
    console.print("[bold]Report[/bold]")
    criteria = model.criteria
    rows: tuple[tuple[str, object], ...] = (
        ("Criteria Filters", "none" if criteria.filters is None else "set"),
        ("Criteria Header Fields", len(criteria.header) if criteria.header else 0),
        ("Criteria Order By", len(criteria.order_by) if criteria.order_by else 0),
        ("Criteria Group By", len(criteria.group_by) if criteria.group_by else 0),
        ("Criteria Page Size", criteria.pagesize),
        ("Criteria Max Rows", criteria.max_rows),
        ("Criteria Grouping Mode", criteria.grouping_mode),
        ("Widgets", len(model.widgets)),
    )
    for label, row_value in rows:
        console.print(f"  [bold]{label}[/bold]: {row_value}")
    for widget in model.widgets:
        console.print(
            f"    - {widget.name} ({widget.title}) "
            f"chart={widget.chart_type} attr={widget.attribute_name}",
        )


def _render_widget_data_detail(model: BaseModel, console: Console) -> None:
    assert isinstance(model, WidgetData)
    console.print("[bold]WidgetData[/bold]")
    console.print(f"  [bold]Enforcements[/bold]: {len(model.enforcements)} bucket(s)")
    for bucket in model.enforcements:
        console.print(
            f"    - hour={bucket.hour} "
            f"allow={bucket.allow_count} deny={bucket.deny_count} "
            f"total={bucket.decision_count}",
        )


register_detail_renderer(PolicyActivityReportDetail, _render_report_detail)
register_detail_renderer(WidgetData, _render_widget_data_detail)
