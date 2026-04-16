from __future__ import annotations

from typing import Annotated

import typer

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, print_success, render
from nextlabs_sdk._cli._parsing import parse_json_payload
from nextlabs_sdk._cloudaz._search import SearchCriteria

component_types_app = typer.Typer(help="Component type management commands")

_CT_COLUMNS = (
    ColumnDef("ID", "id"),
    ColumnDef("Name", "name"),
    ColumnDef("Short Name", "short_name"),
    ColumnDef("Type", "type"),
    ColumnDef("Status", "status"),
)


@component_types_app.command()
@cli_error_handler
def get(
    ctx: typer.Context,
    component_type_id: Annotated[int, typer.Argument(help="Component type ID")],
) -> None:
    """Get a component type by ID."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    ct = client.component_types.get(component_type_id)
    render(cli_ctx, ct, _CT_COLUMNS)


@component_types_app.command()
@cli_error_handler
def create(
    ctx: typer.Context,
    raw_body: Annotated[str, typer.Option("--data", help="JSON payload")],
) -> None:
    """Create a component type from a JSON payload."""
    cli_ctx: CliContext = ctx.obj
    payload = parse_json_payload(raw_body)
    client = _client_factory.make_cloudaz_client(cli_ctx)
    ct_id = client.component_types.create(payload)
    print_success(f"Created component type with ID {ct_id}")


@component_types_app.command()
@cli_error_handler
def modify(
    ctx: typer.Context,
    raw_body: Annotated[str, typer.Option("--data", help="JSON payload")],
) -> None:
    """Modify a component type from a JSON payload."""
    cli_ctx: CliContext = ctx.obj
    payload = parse_json_payload(raw_body)
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
def search(
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
    render(cli_ctx, matches, _CT_COLUMNS, title="Component Types")
