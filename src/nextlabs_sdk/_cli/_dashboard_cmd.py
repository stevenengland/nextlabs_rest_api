from __future__ import annotations

from typing import Annotated

import typer
from pydantic import BaseModel
from rich.console import Console

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._detail_renderers import register_detail_renderer
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, render
from nextlabs_sdk._cli._time_parser import now_epoch_ms, parse_time
from nextlabs_sdk._cloudaz._dashboard_models import PolicyActivity

dashboard_app = typer.Typer(help="Reporter dashboard commands")

_DATE_HELP = (
    "Accepts epoch milliseconds (e.g. 1737014400000), ISO 8601 datetime "
    "(e.g. 2024-01-15 or 2024-01-15T10:30:00+02:00, naive values treated "
    "as UTC), or a relative offset from now (e.g. 30s, 5m, 2h, 3d, 1w)."
)


def _resolve_range(from_date: str, to_date: str | None) -> tuple[int, int]:
    start_ms = parse_time(from_date)
    end_ms = now_epoch_ms() if to_date is None else parse_time(to_date)
    return start_ms, end_ms


_ALERT_COLUMNS = (
    ColumnDef("Level", "level"),
    ColumnDef("Alert Message", "alert_message"),
    ColumnDef("Monitor Name", "monitor_name"),
    ColumnDef("Triggered At", "triggered_at"),
)

_ACTIVITY_COLUMNS = (
    ColumnDef("Name", "name"),
    ColumnDef("Allow", "allow_count"),
    ColumnDef("Deny", "deny_count"),
    ColumnDef("Total", "decision_count"),
)

_TOP_POLICIES_COLUMNS: tuple[ColumnDef, ...] = (
    ColumnDef("Policy", "policy_name"),
    ColumnDef("Days", "day_count"),
    ColumnDef("Allow", "allow_total"),
    ColumnDef("Deny", "deny_total"),
    ColumnDef("Total", "decision_total"),
)

_MONITOR_TAG_ALERT_COLUMNS = (
    ColumnDef("Tag Value", "tag_value"),
    ColumnDef("Monitor Name", "monitor_name"),
    ColumnDef("Alert Count", "alert_count"),
)


@dashboard_app.command()
@cli_error_handler
def alerts(
    ctx: typer.Context,
    from_date: Annotated[str, typer.Option(help=f"Start date. {_DATE_HELP}")],
    to_date: Annotated[
        str | None,
        typer.Option(help=f"End date (defaults to now). {_DATE_HELP}"),
    ] = None,
) -> None:
    """Retrieve latest alerts."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    start_ms, end_ms = _resolve_range(from_date, to_date)
    alerts_list = client.dashboard.latest_alerts(start_ms, end_ms)
    render(cli_ctx, alerts_list, _ALERT_COLUMNS, title="Alerts")


@dashboard_app.command(name="top-users")
@cli_error_handler
def top_users(
    ctx: typer.Context,
    from_date: Annotated[str, typer.Option(help=f"Start date. {_DATE_HELP}")],
    to_date: Annotated[
        str | None,
        typer.Option(help=f"End date (defaults to now). {_DATE_HELP}"),
    ] = None,
    decision: Annotated[str, typer.Option(help="Policy decision filter")] = "AD",
) -> None:
    """Retrieve top users by activity."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    start_ms, end_ms = _resolve_range(from_date, to_date)
    users = client.dashboard.top_users(start_ms, end_ms, decision)
    render(cli_ctx, users, _ACTIVITY_COLUMNS, title="Top Users")


@dashboard_app.command(name="top-resources")
@cli_error_handler
def top_resources(
    ctx: typer.Context,
    from_date: Annotated[str, typer.Option(help=f"Start date. {_DATE_HELP}")],
    to_date: Annotated[
        str | None,
        typer.Option(help=f"End date (defaults to now). {_DATE_HELP}"),
    ] = None,
    decision: Annotated[str, typer.Option(help="Policy decision filter")] = "AD",
) -> None:
    """Retrieve top resources by activity."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    start_ms, end_ms = _resolve_range(from_date, to_date)
    resources = client.dashboard.top_resources(start_ms, end_ms, decision)
    render(cli_ctx, resources, _ACTIVITY_COLUMNS, title="Top Resources")


@dashboard_app.command(name="top-policies")
@cli_error_handler
def top_policies(
    ctx: typer.Context,
    from_date: Annotated[str, typer.Option(help=f"Start date. {_DATE_HELP}")],
    to_date: Annotated[
        str | None,
        typer.Option(help=f"End date (defaults to now). {_DATE_HELP}"),
    ] = None,
    decision: Annotated[str, typer.Option(help="Policy decision filter")] = "AD",
) -> None:
    """Retrieve top policies with daily trend data."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    start_ms, end_ms = _resolve_range(from_date, to_date)
    policies = client.dashboard.top_policies(start_ms, end_ms, decision)
    render(cli_ctx, policies, _TOP_POLICIES_COLUMNS, title="Top Policies")


@dashboard_app.command(name="alerts-by-monitor-tags")
@cli_error_handler
def alerts_by_monitor_tags(
    ctx: typer.Context,
    from_date: Annotated[str, typer.Option(help=f"Start date. {_DATE_HELP}")],
    to_date: Annotated[
        str | None,
        typer.Option(help=f"End date (defaults to now). {_DATE_HELP}"),
    ] = None,
    tag: Annotated[
        list[str] | None,
        typer.Option(
            "--tag",
            help="Filter results to these tag values (repeatable)",
        ),
    ] = None,
) -> None:
    """Retrieve alert counts grouped by monitor tag."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    start_ms, end_ms = _resolve_range(from_date, to_date)
    alerts_list = client.dashboard.alerts_by_monitor_tags(start_ms, end_ms)
    if tag:
        wanted = set(tag)
        alerts_list = [entry for entry in alerts_list if entry.tag_value in wanted]
    render(
        cli_ctx,
        alerts_list,
        _MONITOR_TAG_ALERT_COLUMNS,
        title="Alerts by Monitor Tag",
    )


def _render_policy_activity_detail(model: BaseModel, console: Console) -> None:
    assert isinstance(model, PolicyActivity)
    console.print(f"[bold]Policy[/bold]: {model.policy_name}")
    console.print(
        f"  [bold]Totals[/bold]: allow={model.allow_total} "
        f"deny={model.deny_total} total={model.decision_total} "
        f"days={model.day_count}",
    )
    console.print("  [bold]Daily Trend[/bold]:")
    for bucket in model.policy_decisions:
        console.print(
            f"    - day={bucket.day_nb} "
            f"allow={bucket.allow_count} deny={bucket.deny_count}",
        )


register_detail_renderer(PolicyActivity, _render_policy_activity_detail)
