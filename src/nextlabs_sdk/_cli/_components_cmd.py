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
from nextlabs_sdk._cloudaz._component_models import Component
from nextlabs_sdk._cloudaz._search import SearchCriteria

components_app = typer.Typer(help="Component management commands")

_ID_COLUMN = ColumnDef("ID", "id")
_NAME_COLUMN = ColumnDef("Name", "name")

_COMP_COLUMNS = (
    _ID_COLUMN,
    _NAME_COLUMN,
    ColumnDef("Type", "type"),
    ColumnDef("Status", "status"),
    ColumnDef("Deployed", "deployed"),
)

_COMP_SEARCH_COLUMNS = (
    _ID_COLUMN,
    _NAME_COLUMN,
    ColumnDef("Group", "group"),
    ColumnDef("Status", "status"),
    ColumnDef("Deployed", "deployed"),
)

_COMPONENT_WIDE_COLUMNS: tuple[ColumnDef, ...] = (
    ColumnDef("Created", "created_date"),
    ColumnDef("Updated", "last_updated_date"),
    ColumnDef("Owner", "owner_display_name"),
    ColumnDef("Version", "version"),
)

_DEPENDENCY_COLUMNS = (
    _ID_COLUMN,
    ColumnDef("Type", "type"),
    ColumnDef("Group", "group"),
    _NAME_COLUMN,
    ColumnDef("Folder Path", "folder_path"),
)


@components_app.command()
@cli_error_handler
def get(
    ctx: typer.Context,
    component_id: Annotated[int, typer.Argument(help="Component ID")],
) -> None:
    """Get a component by ID."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)  # noqa: WPS204
    comp = client.components.get(component_id)
    render(cli_ctx, comp, _COMP_COLUMNS, wide_columns=_COMPONENT_WIDE_COLUMNS)


@components_app.command(name="get-active")
@cli_error_handler
def get_active(  # noqa: WPS463
    ctx: typer.Context,
    component_id: Annotated[int, typer.Argument(help="Component ID")],
) -> None:
    """Get the deployed (active) revision of a component by ID."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    comp = client.components.get_active(component_id)
    render(cli_ctx, comp, _COMP_COLUMNS, wide_columns=_COMPONENT_WIDE_COLUMNS)


@components_app.command(name="create-sub")
@cli_error_handler
def create_sub(
    ctx: typer.Context,
    parent_id: Annotated[
        int,
        typer.Option("--parent-id", help="Parent component ID"),
    ],
    payload_path: Annotated[
        Path | None,
        typer.Option("--payload", help="Path to a JSON payload file"),
    ] = None,
) -> None:
    """Create a sub-component under ``--parent-id`` from a JSON payload."""
    payload = require_payload(payload_path)
    payload["parentId"] = parent_id
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    comp_id = client.components.create_sub_component(payload)
    print_success(f"Created sub-component with ID {comp_id}")


@components_app.command(name="bulk-delete")
@cli_error_handler
def bulk_delete(
    ctx: typer.Context,
    ids: Annotated[
        list[int] | None,
        typer.Option("--id", help="Component ID (repeatable)"),
    ] = None,
    ids_csv: Annotated[
        str | None,
        typer.Option("--ids", help="Comma-separated component IDs"),
    ] = None,
) -> None:
    """Delete several components in a single request."""
    resolved = parse_bulk_ids(ids, ids_csv)
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.components.bulk_delete(resolved)
    print_success(f"Deleted {len(resolved)} components")


@components_app.command(name="find-dependencies")
@cli_error_handler
def find_dependencies(
    ctx: typer.Context,
    component_id: Annotated[int, typer.Argument(help="Component ID")],
) -> None:
    """List entities that depend on a component."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    deps = client.components.find_dependencies([component_id])
    render(cli_ctx, deps, _DEPENDENCY_COLUMNS, title="Dependencies")


@components_app.command()
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
    """Create a component from a JSON payload file."""
    reject_data_flag(legacy_data)
    payload = require_payload(payload_path)
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    comp_id = client.components.create(payload)
    print_success(f"Created component with ID {comp_id}")


@components_app.command()
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
    """Modify a component from a JSON payload file."""
    reject_data_flag(legacy_data)
    payload = require_payload(payload_path)
    cli_ctx: CliContext = ctx.obj
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
    render(
        cli_ctx,
        matches,
        _COMP_SEARCH_COLUMNS,
        title="Components",
        wide_columns=_COMPONENT_WIDE_COLUMNS,
    )


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


def _render_component_detail(model: BaseModel, console: Console) -> None:
    assert isinstance(model, Component)
    console.print(f"[bold]Component[/bold] {model.id}")
    policy_model_label = (
        None
        if model.policy_model is None
        else f"{model.policy_model.id} ({model.policy_model.name})"
    )
    deployment_request_label = (
        None if model.deployment_request is None else str(model.deployment_request.id)
    )
    scalar_rows: tuple[tuple[str, object], ...] = (
        ("Name", model.name),
        ("Description", model.description),
        ("Type", model.type.value),
        ("Category", model.category),
        ("Status", model.status.value),
        ("Folder ID", model.folder_id),
        ("Folder Path", model.folder_path),
        ("Parent ID", model.parent_id),
        ("Parent Name", model.parent_name),
        ("Policy Model", policy_model_label),
        ("Action Type", model.action_type),
        ("Deployed", model.deployed),
        ("Deployment Time", model.deployment_time),
        ("Deployment Pending", model.deployment_pending),
        ("Deployment Request", deployment_request_label),
        ("Revision Count", model.revision_count),
        ("Version", model.version),
        ("Hidden", model.hidden),
        ("Pre Created", model.pre_created),
        ("Has Inactive Sub Components", model.has_inactive_sub_components),
        ("Skip Validate", model.skip_validate),
        ("Re-Index All Now", model.re_index_all_now),
        ("Owner ID", model.owner_id),
        ("Owner Display Name", model.owner_display_name),
        ("Created Date", model.created_date),
        ("Last Updated Date", model.last_updated_date),
        ("Modified By ID", model.modified_by_id),
        ("Modified By", model.modified_by),
    )
    count_rows: tuple[tuple[str, int], ...] = (
        ("Tags", len(model.tags)),
        ("Actions", len(model.actions)),
        ("Conditions", len(model.conditions)),
        ("Member Conditions", len(model.member_conditions)),
        ("Sub Components", len(model.sub_components)),
        ("Authorities", len(model.authorities)),
    )
    for label, scalar_value in scalar_rows:
        console.print(f"  [bold]{label}[/bold]: {scalar_value}")
    for label, count in count_rows:
        console.print(f"  [bold]{label}[/bold]: {count} defined")


register_detail_renderer(Component, _render_component_detail)
