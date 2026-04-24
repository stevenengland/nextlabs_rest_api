"""CLI commands for the Reporter activity-logs service."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._activity_log_query_builder import build_activity_log_query
from nextlabs_sdk._cli._binary_output import write_bytes
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, render

activity_logs_app = typer.Typer(help="Report activity log commands.")

_ENFORCEMENT_COLUMNS = (
    ColumnDef("Row ID", "row_id"),
    ColumnDef("Time", "time"),
    ColumnDef("User", "user_name"),
    ColumnDef("Policy", "policy_name"),
    ColumnDef("Decision", "policy_decision"),
    ColumnDef("Action", "action"),
)

_ENFORCEMENT_WIDE_COLUMNS: tuple[ColumnDef, ...] = (
    ColumnDef("Resource", "from_resource_name"),
    ColumnDef("From Resource Path", "from_resource_path"),
    ColumnDef("To Resource", "to_resource_name"),
    ColumnDef("Short Code", "action_short_code"),
    ColumnDef("Log Level", "log_level"),
)

_DEFAULT_HEADER_COLUMNS: tuple[str, ...] = (
    "ROW_ID",
    "TIME",
    "USER_NAME",
    "FROM_RESOURCE_NAME",
    "POLICY_NAME",
    "POLICY_DECISION",
    "ACTION",
)

_ATTRIBUTE_COLUMNS = (
    ColumnDef("Name", "name"),
    ColumnDef("Value", "value"),
    ColumnDef("Data Type", "data_type"),
    ColumnDef("Attr Type", "attr_type"),
    ColumnDef("Dynamic", "is_dynamic"),
)


_DATE_HELP = (
    "Accepts epoch milliseconds (e.g. 1737014400000), ISO 8601 datetime "
    "(e.g. 2024-01-15 or 2024-01-15T10:30:00+02:00, naive values treated "
    "as UTC), or a relative offset from now (e.g. 30s, 5m, 2h, 3d, 1w)."
)


@activity_logs_app.command()
@cli_error_handler
def search(  # noqa: WPS211
    ctx: typer.Context,
    query: Annotated[
        Path | None,
        typer.Option("--query", help="Path to a JSON query file"),
    ] = None,
    policy_decision: Annotated[
        str | None,
        typer.Option("--policy-decision", help="Policy decision filter"),
    ] = None,
    sort_by: Annotated[str | None, typer.Option("--sort-by", help="Sort field")] = None,
    sort_order: Annotated[
        str | None, typer.Option("--sort-order", help="Sort order")
    ] = None,
    field_name: Annotated[
        str | None, typer.Option("--field-name", help="Filter field name")
    ] = None,
    field_value: Annotated[
        str | None, typer.Option("--field-value", help="Filter field value")
    ] = None,
    from_date: Annotated[
        str | None, typer.Option("--from-date", help=f"Start date. {_DATE_HELP}")
    ] = None,
    to_date: Annotated[
        str | None, typer.Option("--to-date", help=f"End date. {_DATE_HELP}")
    ] = None,
    header: Annotated[
        list[str] | None,
        typer.Option("--header", help="Header name (repeatable)"),
    ] = None,
    page_size: Annotated[
        int, typer.Option("--page-size", help="Entries per page")
    ] = 20,
) -> None:
    """Search activity logs (first page of results).

    Inline flags may be combined with ``--query PATH``. When both are
    supplied, inline flag values override the corresponding keys in the
    file. When ``--query`` is omitted, ``--field-name`` and
    ``--field-value`` are required; other optional fields fall back to
    spec-example defaults.

    Live reporter servers have been observed to return 500 when
    ``toDate`` or ``header`` are absent. In inline-build mode this
    command therefore defaults ``toDate`` to now when ``--from-date`` is
    supplied without ``--to-date``, and populates ``header`` with the
    OpenAPI spec's example column set (``ROW_ID``, ``TIME``,
    ``USER_NAME``, ``FROM_RESOURCE_NAME``, ``POLICY_NAME``,
    ``POLICY_DECISION``, ``ACTION``) when ``--header`` is not given.
    Non-example columns have been observed to be rejected by live
    servers; pass ``--header`` explicitly to request additional columns
    your deployment supports. Payloads loaded via ``--query PATH`` are
    forwarded verbatim.
    """
    cli_ctx: CliContext = ctx.obj
    log_query = build_activity_log_query(
        query,
        policy_decision=policy_decision,
        sort_by=sort_by,
        sort_order=sort_order,
        field_name=field_name,
        field_value=field_value,
        from_date=from_date,
        to_date=to_date,
        header=header,
        default_header=list(_DEFAULT_HEADER_COLUMNS),
    )
    client = _client_factory.make_cloudaz_client(cli_ctx)
    paginator = client.activity_logs.search(log_query, page_size=page_size)
    page = paginator.first_page()
    render(
        cli_ctx,
        page.entries,
        _ENFORCEMENT_COLUMNS,
        title="Activity Logs",
        wide_columns=_ENFORCEMENT_WIDE_COLUMNS,
    )


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
def export(  # noqa: WPS211
    ctx: typer.Context,
    output: Annotated[
        Path,
        typer.Option("--output", help="Destination file path"),
    ],
    query: Annotated[
        Path | None,
        typer.Option("--query", help="Path to a JSON query file"),
    ] = None,
    policy_decision: Annotated[
        str | None,
        typer.Option("--policy-decision", help="Policy decision filter"),
    ] = None,
    sort_by: Annotated[str | None, typer.Option("--sort-by", help="Sort field")] = None,
    sort_order: Annotated[
        str | None, typer.Option("--sort-order", help="Sort order")
    ] = None,
    field_name: Annotated[
        str | None, typer.Option("--field-name", help="Filter field name")
    ] = None,
    field_value: Annotated[
        str | None, typer.Option("--field-value", help="Filter field value")
    ] = None,
    from_date: Annotated[
        str | None, typer.Option("--from-date", help=f"Start date. {_DATE_HELP}")
    ] = None,
    to_date: Annotated[
        str | None, typer.Option("--to-date", help=f"End date. {_DATE_HELP}")
    ] = None,
    header: Annotated[
        list[str] | None,
        typer.Option("--header", help="Header name (repeatable)"),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite/--no-overwrite", help="Replace existing file"),
    ] = False,
) -> None:
    """Export matching activity logs as raw bytes to ``--output``.

    Inline flags follow the same merge semantics as ``search``: they
    override keys from ``--query PATH`` when both are supplied. In
    inline-build mode ``toDate`` and ``header`` are defaulted the same
    way as ``search`` to satisfy live reporter servers that reject
    payloads missing those fields.
    """
    cli_ctx: CliContext = ctx.obj
    log_query = build_activity_log_query(
        query,
        policy_decision=policy_decision,
        sort_by=sort_by,
        sort_order=sort_order,
        field_name=field_name,
        field_value=field_value,
        from_date=from_date,
        to_date=to_date,
        header=header,
        default_header=list(_DEFAULT_HEADER_COLUMNS),
    )
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
