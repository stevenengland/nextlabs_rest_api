from __future__ import annotations

from typing import Annotated

import typer

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, print_success, render
from nextlabs_sdk._cli._parsing import parse_json_payload
from nextlabs_sdk._cloudaz._search import SearchCriteria

components_app = typer.Typer(help="Component management commands")

_COMP_COLUMNS = (
    ColumnDef("ID", "id"),
    ColumnDef("Name", "name"),
    ColumnDef("Type", "type"),
    ColumnDef("Status", "status"),
    ColumnDef("Deployed", "deployed"),
)

_COMP_SEARCH_COLUMNS = (
    ColumnDef("ID", "id"),
    ColumnDef("Name", "name"),
    ColumnDef("Group", "group"),
    ColumnDef("Status", "status"),
    ColumnDef("Deployed", "deployed"),
)


@components_app.command()
@cli_error_handler
def get(
    ctx: typer.Context,
    component_id: Annotated[int, typer.Argument(help="Component ID")],
) -> None:
    """Get a component by ID."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    comp = client.components.get(component_id)
    render(cli_ctx, comp, _COMP_COLUMNS)


@components_app.command()
@cli_error_handler
def create(
    ctx: typer.Context,
    raw_body: Annotated[str, typer.Option("--data", help="JSON payload")],
) -> None:
    """Create a component from a JSON payload."""
    cli_ctx: CliContext = ctx.obj
    payload = parse_json_payload(raw_body)
    client = _client_factory.make_cloudaz_client(cli_ctx)
    comp_id = client.components.create(payload)
    print_success(f"Created component with ID {comp_id}")


@components_app.command()
@cli_error_handler
def modify(
    ctx: typer.Context,
    raw_body: Annotated[str, typer.Option("--data", help="JSON payload")],
) -> None:
    """Modify a component from a JSON payload."""
    cli_ctx: CliContext = ctx.obj
    payload = parse_json_payload(raw_body)
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.components.modify(payload)
    print_success("Modified component")


@components_app.command()
@cli_error_handler
def delete(
    ctx: typer.Context,
    component_id: Annotated[int, typer.Argument(help="Component ID")],
) -> None:
    """Delete a component by ID."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.components.delete(component_id)
    print_success(f"Deleted component {component_id}")


def _build_criteria(
    group: str | None,
    status: str | None,
    text: str | None,
    tag: str | None,
    sort: str | None,
) -> SearchCriteria:
    criteria = SearchCriteria()
    if group:
        criteria.filter_group(group)
    if status:
        criteria.filter_status(status)
    if text:
        criteria.filter_text(text)
    if tag:
        criteria.filter_tags(tag)
    if sort:
        criteria.sort_by(sort)
    return criteria


@components_app.command()
@cli_error_handler
def search(
    ctx: typer.Context,
    group: Annotated[
        str | None,
        typer.Option(help="Filter by group (SUBJECT, RESOURCE, ACTION)"),
    ] = None,
    status: Annotated[
        str | None,
        typer.Option(help="Filter by status (DRAFT, APPROVED)"),
    ] = None,
    text: Annotated[str | None, typer.Option(help="Text search")] = None,
    tag: Annotated[str | None, typer.Option(help="Filter by tag key")] = None,
    sort: Annotated[
        str | None,
        typer.Option(help="Sort field (e.g. name)"),
    ] = None,
    page_size: Annotated[int, typer.Option(help="Results per page")] = 20,
) -> None:
    """Search components."""
    cli_ctx: CliContext = ctx.obj
    criteria = _build_criteria(group, status, text, tag, sort)
    criteria.page(page_no=1, page_size=page_size)
    client = _client_factory.make_cloudaz_client(cli_ctx)
    matches = list(client.component_search.search(criteria))
    render(cli_ctx, matches, _COMP_SEARCH_COLUMNS, title="Components")


@components_app.command()
@cli_error_handler
def deploy(
    ctx: typer.Context,
    component_id: Annotated[int, typer.Argument(help="Component ID")],
    push: Annotated[bool, typer.Option(help="Push deploy to PDP")] = False,
) -> None:
    """Deploy a component."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.components.deploy([{"id": component_id, "push": push}])
    print_success(f"Deployed component {component_id}")


@components_app.command()
@cli_error_handler
def undeploy(
    ctx: typer.Context,
    component_id: Annotated[int, typer.Argument(help="Component ID")],
) -> None:
    """Undeploy a component."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.components.undeploy([component_id])
    print_success(f"Undeployed component {component_id}")
