from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel
from rich.console import Console

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._bulk_ids import parse_bulk_ids
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._detail_renderers import register_detail_renderer
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, print_success, render
from nextlabs_sdk._cli._payload_loader import reject_data_flag, require_payload
from nextlabs_sdk._cloudaz._component_type_models import ComponentType
from nextlabs_sdk._cloudaz._search import SearchCriteria

component_types_app = typer.Typer(help="Component type management commands")

_CT_COLUMNS = (
    ColumnDef("ID", "id"),
    ColumnDef("Name", "name"),
    ColumnDef("Short Name", "short_name"),
    ColumnDef("Type", "type"),
    ColumnDef("Status", "status"),
)

_CT_WIDE_COLUMNS: tuple[ColumnDef, ...] = (
    ColumnDef("Description", "description"),
    ColumnDef("Owner", "owner_display_name"),
    ColumnDef("Created", "created_date"),
    ColumnDef("Updated", "last_updated_date"),
    ColumnDef("Version", "version"),
)

_ATTRIBUTE_CONFIG_COLUMNS = (
    ColumnDef("ID", "id"),
    ColumnDef("Name", "name"),
    ColumnDef("Short Name", "short_name"),
    ColumnDef("Data Type", "data_type"),
    ColumnDef("Sort Order", "sort_order"),
)

_ATTRIBUTE_CONFIG_WIDE_COLUMNS: tuple[ColumnDef, ...] = (
    ColumnDef("Regex Pattern", "reg_ex_pattern"),
    ColumnDef("Version", "version"),
)


@component_types_app.command()
@cli_error_handler
def get(
    ctx: typer.Context,
    component_type_id: Annotated[int, typer.Argument(help="Component type ID")],
) -> None:
    """Get a component type by ID."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)  # noqa: WPS204
    ct = client.component_types.get(component_type_id)
    render(cli_ctx, ct, _CT_COLUMNS, wide_columns=_CT_WIDE_COLUMNS)


@component_types_app.command(name="get-active")
@cli_error_handler
def get_active(  # noqa: WPS463
    ctx: typer.Context,
    component_type_id: Annotated[int, typer.Argument(help="Component type ID")],
) -> None:
    """Get the deployed (active) revision of a component type by ID."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    ct = client.component_types.get_active(component_type_id)
    render(cli_ctx, ct, _CT_COLUMNS, wide_columns=_CT_WIDE_COLUMNS)


@component_types_app.command(name="bulk-delete")
@cli_error_handler
def bulk_delete(
    ctx: typer.Context,
    ids: Annotated[
        list[int] | None,
        typer.Option("--id", help="Component type ID (repeatable)"),
    ] = None,
    ids_csv: Annotated[
        str | None,
        typer.Option("--ids", help="Comma-separated component type IDs"),
    ] = None,
) -> None:
    """Delete several component types in a single request."""
    resolved = parse_bulk_ids(ids, ids_csv)
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.component_types.bulk_delete(resolved)
    print_success(f"Deleted {len(resolved)} component types")


@component_types_app.command()
@cli_error_handler
def clone(
    ctx: typer.Context,
    component_type_id: Annotated[int, typer.Argument(help="Component type ID")],
) -> None:
    """Clone a component type and print the new ID."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    new_id = client.component_types.clone(component_type_id)
    print_success(f"Cloned component type; new ID {new_id}")


@component_types_app.command(name="list-extra-subject-attributes")
@cli_error_handler
def list_extra_subject_attributes(
    ctx: typer.Context,
    component_type: Annotated[
        str, typer.Argument(help="Component type short name (e.g. USER)")
    ],
) -> None:
    """List extra subject attribute configs for a component type."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    attrs = client.component_types.list_extra_subject_attributes(component_type)
    render(
        cli_ctx,
        attrs,
        _ATTRIBUTE_CONFIG_COLUMNS,
        title="Extra Subject Attributes",
        wide_columns=_ATTRIBUTE_CONFIG_WIDE_COLUMNS,
    )


@component_types_app.command()
@cli_error_handler
def create(
    ctx: typer.Context,
    payload_path: Annotated[
        Path | None,
        typer.Option("--payload", help="Path to a JSON payload file"),
    ] = None,
    legacy_data: Annotated[
        str | None,
        typer.Option("--data", hidden=True),
    ] = None,
) -> None:
    """Create a component type from a JSON payload file."""
    reject_data_flag(legacy_data)
    payload = require_payload(payload_path)
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    ct_id = client.component_types.create(payload)
    print_success(f"Created component type with ID {ct_id}")


@component_types_app.command()
@cli_error_handler
def modify(
    ctx: typer.Context,
    payload_path: Annotated[
        Path | None,
        typer.Option("--payload", help="Path to a JSON payload file"),
    ] = None,
    legacy_data: Annotated[
        str | None,
        typer.Option("--data", hidden=True),
    ] = None,
) -> None:
    """Modify a component type from a JSON payload file."""
    reject_data_flag(legacy_data)
    payload = require_payload(payload_path)
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.component_types.modify(payload)
    print_success("Modified component type")


@component_types_app.command()
@cli_error_handler
def delete(
    ctx: typer.Context,
    component_type_id: Annotated[int, typer.Argument(help="Component type ID")],
) -> None:
    """Delete a component type by ID."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.component_types.delete(component_type_id)
    print_success(f"Deleted component type {component_type_id}")


def _build_criteria(
    type_filter: str | None,
    text: str | None,
    tag: str | None,
    sort: str | None,
) -> SearchCriteria:
    criteria = SearchCriteria()
    if type_filter:
        criteria.filter_type(type_filter)
    if text:
        criteria.filter_text(text)
    if tag:
        criteria.filter_tags(tag)
    if sort:
        criteria.sort_by(sort)
    return criteria


@component_types_app.command()
@cli_error_handler
def search(  # noqa: WPS211
    ctx: typer.Context,
    type_filter: Annotated[
        str | None,
        typer.Option("--type", help="Filter by type (e.g. RESOURCE, SUBJECT)"),
    ] = None,
    text: Annotated[str | None, typer.Option(help="Text search")] = None,
    tag: Annotated[str | None, typer.Option(help="Filter by tag key")] = None,
    sort: Annotated[str | None, typer.Option(help="Sort field (e.g. name)")] = None,
    page_size: Annotated[int, typer.Option(help="Results per page")] = 20,
) -> None:
    """Search component types."""
    cli_ctx: CliContext = ctx.obj
    criteria = _build_criteria(type_filter, text, tag, sort)
    criteria.page(page_no=1, page_size=page_size)
    client = _client_factory.make_cloudaz_client(cli_ctx)
    matches = list(client.component_type_search.search(criteria))
    render(
        cli_ctx,
        matches,
        _CT_COLUMNS,
        title="Component Types",
        wide_columns=_CT_WIDE_COLUMNS,
    )


def _render_component_type_detail(model: BaseModel, console: Console) -> None:
    assert isinstance(model, ComponentType)
    console.print(f"[bold]ComponentType[/bold] {model.id}")
    scalar_rows: tuple[tuple[str, object], ...] = (
        ("Name", model.name),
        ("Short Name", model.short_name),
        ("Description", model.description),
        ("Type", model.type.value),
        ("Status", model.status),
        ("Version", model.version),
        ("Owner ID", model.owner_id),
        ("Owner Display Name", model.owner_display_name),
        ("Created Date", model.created_date),
        ("Last Updated Date", model.last_updated_date),
        ("Modified By ID", model.modified_by_id),
        ("Modified By", model.modified_by),
    )
    count_rows: tuple[tuple[str, int], ...] = (
        ("Tags", len(model.tags)),
        ("Attributes", len(model.attributes)),
        ("Actions", len(model.actions)),
        ("Obligations", len(model.obligations)),
    )
    for label, scalar_value in scalar_rows:
        console.print(f"  [bold]{label}[/bold]: {scalar_value}")
    for label, count in count_rows:
        console.print(f"  [bold]{label}[/bold]: {count} defined")


register_detail_renderer(ComponentType, _render_component_type_detail)
