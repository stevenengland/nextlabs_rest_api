from __future__ import annotations

from typing import Annotated

import typer

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, render, render_json

dashboard_app = typer.Typer(help="Reporter dashboard commands")

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


@dashboard_app.command()
@cli_error_handler
def alerts(
    ctx: typer.Context,
    from_date: Annotated[int, typer.Option(help="Start date (epoch ms)")],
    to_date: Annotated[int, typer.Option(help="End date (epoch ms)")],
) -> None:
    """Retrieve latest alerts."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    alerts_list = client.dashboard.latest_alerts(from_date, to_date)
    render(cli_ctx, alerts_list, _ALERT_COLUMNS, title="Alerts")


@dashboard_app.command(name="top-users")
@cli_error_handler
def top_users(
    ctx: typer.Context,
    from_date: Annotated[int, typer.Option(help="Start date (epoch ms)")],
    to_date: Annotated[int, typer.Option(help="End date (epoch ms)")],
    decision: Annotated[str, typer.Option(help="Policy decision filter")] = "AD",
) -> None:
    """Retrieve top users by activity."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    users = client.dashboard.top_users(from_date, to_date, decision)
    render(cli_ctx, users, _ACTIVITY_COLUMNS, title="Top Users")


@dashboard_app.command(name="top-resources")
@cli_error_handler
def top_resources(
    ctx: typer.Context,
    from_date: Annotated[int, typer.Option(help="Start date (epoch ms)")],
    to_date: Annotated[int, typer.Option(help="End date (epoch ms)")],
    decision: Annotated[str, typer.Option(help="Policy decision filter")] = "AD",
) -> None:
    """Retrieve top resources by activity."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    resources = client.dashboard.top_resources(from_date, to_date, decision)
    render(cli_ctx, resources, _ACTIVITY_COLUMNS, title="Top Resources")


@dashboard_app.command(name="top-policies")
@cli_error_handler
def top_policies(
    ctx: typer.Context,
    from_date: Annotated[int, typer.Option(help="Start date (epoch ms)")],
    to_date: Annotated[int, typer.Option(help="End date (epoch ms)")],
    decision: Annotated[str, typer.Option(help="Policy decision filter")] = "AD",
) -> None:
    """Retrieve top policies with daily trend data."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    policies = client.dashboard.top_policies(from_date, to_date, decision)
    render_json(policies)
