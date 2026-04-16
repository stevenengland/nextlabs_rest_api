from __future__ import annotations

import json as json_mod
from pathlib import Path
from typing import Annotated

import typer

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, print_error, print_success, render
from nextlabs_sdk._cloudaz._search import SearchCriteria

policies_app = typer.Typer(help="Policy management commands")

_POLICY_COLUMNS = (
    ColumnDef("ID", "id"),
    ColumnDef("Name", "name"),
    ColumnDef("Status", "status"),
    ColumnDef("Effect", "effect_type"),
    ColumnDef("Deployed", "deployed"),
)


def _parse_json(raw: str) -> dict[str, object]:
    try:
        parsed = json_mod.loads(raw)
    except json_mod.JSONDecodeError:
        print_error("Invalid JSON payload")
        raise typer.Exit(code=1)
    if not isinstance(parsed, dict):
        print_error("JSON payload must be an object")
        raise typer.Exit(code=1)
    return parsed


@policies_app.command()
@cli_error_handler
def get(
    ctx: typer.Context,
    policy_id: Annotated[int, typer.Argument(help="Policy ID")],
) -> None:
    """Get a policy by ID."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    policy = client.policies.get(policy_id)
    render(cli_ctx, policy, _POLICY_COLUMNS)


@policies_app.command()
@cli_error_handler
def create(
    ctx: typer.Context,
    raw_body: Annotated[str, typer.Option("--data", help="JSON payload")],
) -> None:
    """Create a policy from a JSON payload."""
    cli_ctx: CliContext = ctx.obj
    payload = _parse_json(raw_body)
    client = _client_factory.make_cloudaz_client(cli_ctx)
    policy_id = client.policies.create(payload)
    print_success(f"Created policy with ID {policy_id}")


@policies_app.command()
@cli_error_handler
def modify(
    ctx: typer.Context,
    raw_body: Annotated[str, typer.Option("--data", help="JSON payload")],
) -> None:
    """Modify a policy from a JSON payload."""
    cli_ctx: CliContext = ctx.obj
    payload = _parse_json(raw_body)
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.policies.modify(payload)
    print_success("Modified policy")


@policies_app.command()
@cli_error_handler
def delete(
    ctx: typer.Context,
    policy_id: Annotated[int, typer.Argument(help="Policy ID")],
) -> None:
    """Delete a policy by ID."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.policies.delete(policy_id)
    print_success(f"Deleted policy {policy_id}")


@policies_app.command()
@cli_error_handler
def search(
    ctx: typer.Context,
    status: Annotated[
        str | None, typer.Option(help="Filter by status (DRAFT, APPROVED)")
    ] = None,
    effect: Annotated[
        str | None, typer.Option(help="Filter by effect type (ALLOW, DENY)")
    ] = None,
    text: Annotated[str | None, typer.Option(help="Text search")] = None,
    tag: Annotated[str | None, typer.Option(help="Filter by tag key")] = None,
    sort: Annotated[str | None, typer.Option(help="Sort field (e.g. name)")] = None,
    page_size: Annotated[int, typer.Option(help="Results per page")] = 20,
) -> None:
    """Search policies."""
    cli_ctx: CliContext = ctx.obj
    criteria = SearchCriteria()
    if status:
        criteria.filter_status(status)
    if effect:
        criteria.filter_effect_type(effect)
    if text:
        criteria.filter_text(text)
    if tag:
        criteria.filter_tags(tag)
    if sort:
        criteria.sort_by(sort)
    criteria.page(page_no=1, page_size=page_size)
    client = _client_factory.make_cloudaz_client(cli_ctx)
    matches = list(client.policy_search.search(criteria))
    render(cli_ctx, matches, _POLICY_COLUMNS, title="Policies")


@policies_app.command()
@cli_error_handler
def deploy(
    ctx: typer.Context,
    policy_id: Annotated[int, typer.Argument(help="Policy ID")],
    push: Annotated[bool, typer.Option(help="Push deploy to PDP")] = False,
) -> None:
    """Deploy a policy."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.policies.deploy([{"id": policy_id, "push": push}])
    print_success(f"Deployed policy {policy_id}")


@policies_app.command()
@cli_error_handler
def undeploy(
    ctx: typer.Context,
    policy_id: Annotated[int, typer.Argument(help="Policy ID")],
) -> None:
    """Undeploy a policy."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.policies.undeploy([policy_id])
    print_success(f"Undeployed policy {policy_id}")


@policies_app.command(name="export")
@cli_error_handler
def export_policy(
    ctx: typer.Context,
    policy_id: Annotated[int, typer.Argument(help="Policy ID")],
    export_mode: Annotated[
        str, typer.Option("--mode", help="Export mode (PLAIN, SANDE)")
    ] = "PLAIN",
) -> None:
    """Export a policy."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    exported = client.policies.export(
        [{"id": policy_id}],
        export_mode=export_mode,
    )
    print(exported)


@policies_app.command(name="import-policies")
@cli_error_handler
def import_policies(
    ctx: typer.Context,
    file_path: Annotated[str, typer.Option("--file", help="Path to import file")],
    mechanism: Annotated[
        str, typer.Option(help="Import mechanism (PARTIAL, OVERWRITE)")
    ] = "PARTIAL",
    cleanup: Annotated[bool, typer.Option(help="Clean up after import")] = False,
) -> None:
    """Import policies from a file."""
    cli_ctx: CliContext = ctx.obj
    path = Path(file_path)
    if not path.exists():
        print_error(f"File not found: {file_path}")
        raise typer.Exit(code=1)
    file_bytes = path.read_bytes()
    files = {"file": (path.name, file_bytes, "application/octet-stream")}
    client = _client_factory.make_cloudaz_client(cli_ctx)
    import_result = client.policies.import_policies(
        files,
        import_mechanism=mechanism,
        cleanup=cleanup,
    )
    print_success(
        f"Imported {import_result.total_policies} policies, "
        f"{import_result.total_components} components, "
        f"{import_result.total_policy_models} policy models",
    )
