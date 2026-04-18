from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel
from rich.console import Console

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._binary_output import write_bytes
from nextlabs_sdk._cli._bulk_ids import parse_bulk_ids
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._detail_renderers import register_detail_renderer
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, print_error, print_success, render
from nextlabs_sdk._cli._payload_loader import (
    load_payload,
    reject_data_flag,
    require_payload,
)
from nextlabs_sdk._cloudaz._policy_models import Policy
from nextlabs_sdk._cloudaz._search import SearchCriteria

policies_app = typer.Typer(help="Policy management commands")

_ID_FIELD = "id"
_ID_COLUMN = ColumnDef("ID", _ID_FIELD)

_POLICY_COLUMNS = (
    _ID_COLUMN,
    ColumnDef("Name", "name"),
    ColumnDef("Status", "status"),
    ColumnDef("Effect", "effect_type"),
    ColumnDef("Deployed", "deployed"),
)

_POLICY_WIDE_COLUMNS: tuple[ColumnDef, ...] = (
    ColumnDef("Created", "created_date"),
    ColumnDef("Updated", "last_updated_date"),
    ColumnDef("Owner", "owner_display_name"),
    ColumnDef("Version", "version"),
)

_DEPENDENCY_COLUMNS = (
    _ID_COLUMN,
    ColumnDef("Type", "type"),
    ColumnDef("Group", "group"),
    ColumnDef("Name", "name"),
    ColumnDef("Folder Path", "folder_path"),
)

_EXPORT_OPTIONS_COLUMNS = (
    ColumnDef("Plain Text Enabled", "plain_text_enabled"),
    ColumnDef("SANDE Enabled", "sande_enabled"),
)

_IMPORT_RESULT_COLUMNS = (
    ColumnDef("Policies", "total_policies"),
    ColumnDef("Components", "total_components"),
    ColumnDef("Policy Models", "total_policy_models"),
    ColumnDef("Non-Blocking Error", "non_blocking_error"),
)


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
    render(cli_ctx, policy, _POLICY_COLUMNS, wide_columns=_POLICY_WIDE_COLUMNS)


@policies_app.command(name="get-active")
@cli_error_handler
def get_active(  # noqa: WPS463
    ctx: typer.Context,
    policy_id: Annotated[int, typer.Argument(help="Policy ID")],
) -> None:
    """Get the deployed (active) revision of a policy by ID."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    policy = client.policies.get_active(policy_id)
    render(cli_ctx, policy, _POLICY_COLUMNS, wide_columns=_POLICY_WIDE_COLUMNS)


@policies_app.command(name="create-sub")
@cli_error_handler
def create_sub(
    ctx: typer.Context,
    parent_id: Annotated[int, typer.Option("--parent-id", help="Parent policy ID")],
    payload_path: Annotated[
        Path | None,
        typer.Option("--payload", help="Path to a JSON payload file"),
    ] = None,
) -> None:
    """Create a sub-policy under ``--parent-id`` from a JSON payload."""
    payload = require_payload(payload_path)
    payload["parentId"] = parent_id
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    policy_id = client.policies.create_sub_policy(payload)
    print_success(f"Created sub-policy with ID {policy_id}")


@policies_app.command(name="bulk-delete")
@cli_error_handler
def bulk_delete(
    ctx: typer.Context,
    ids: Annotated[
        list[int] | None,
        typer.Option("--id", help="Policy ID (repeatable)"),
    ] = None,
    ids_csv: Annotated[
        str | None,
        typer.Option("--ids", help="Comma-separated policy IDs"),
    ] = None,
) -> None:
    """Delete several policies in a single request."""
    resolved = parse_bulk_ids(ids, ids_csv)
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.policies.bulk_delete(resolved)
    print_success(f"Deleted {len(resolved)} policies")


@policies_app.command(name="bulk-delete-xacml")
@cli_error_handler
def bulk_delete_xacml(
    ctx: typer.Context,
    ids: Annotated[
        list[int] | None,
        typer.Option("--id", help="XACML policy ID (repeatable)"),
    ] = None,
    ids_csv: Annotated[
        str | None,
        typer.Option("--ids", help="Comma-separated XACML policy IDs"),
    ] = None,
) -> None:
    """Delete several XACML-only policies in a single request."""
    resolved = parse_bulk_ids(ids, ids_csv)
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.policies.bulk_delete_xacml(resolved)
    print_success(f"Deleted {len(resolved)} XACML policies")


@policies_app.command(name="find-dependencies")
@cli_error_handler
def find_dependencies(
    ctx: typer.Context,
    policy_id: Annotated[int, typer.Argument(help="Policy ID")],
) -> None:
    """List entities that depend on a policy."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    deps = client.policies.find_dependencies([policy_id])
    render(cli_ctx, deps, _DEPENDENCY_COLUMNS, title="Dependencies")


@policies_app.command(name="export-all")
@cli_error_handler
def export_all(
    ctx: typer.Context,
    output: Annotated[
        Path,
        typer.Option("--output", help="Destination file path"),
    ],
    export_mode: Annotated[
        str, typer.Option("--mode", help="Export mode (PLAIN, SANDE)")
    ] = "PLAIN",
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite/--no-overwrite", help="Replace existing file"),
    ] = False,
) -> None:
    """Export every policy as bytes to ``--output``."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    exported = client.policies.export_all(export_mode=export_mode)
    write_bytes(output, exported.encode("utf-8"), overwrite=overwrite)


@policies_app.command(name="export-options")
@cli_error_handler
def export_options(ctx: typer.Context) -> None:
    """Show the export modes the server supports."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    options = client.policies.export_options()
    render(cli_ctx, options, _EXPORT_OPTIONS_COLUMNS)


@policies_app.command(name="generate-xacml")
@cli_error_handler
def generate_xacml(
    ctx: typer.Context,
    policy_id: Annotated[int, typer.Argument(help="Policy ID")],
    output: Annotated[
        Path,
        typer.Option("--output", help="Destination file path"),
    ],
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite/--no-overwrite", help="Replace existing file"),
    ] = False,
) -> None:
    """Generate a XACML artifact for the given policy."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    xacml = client.policies.generate_xacml([{_ID_FIELD: policy_id}])
    write_bytes(output, xacml.encode("utf-8"), overwrite=overwrite)


@policies_app.command(name="generate-pdf")
@cli_error_handler
def generate_pdf(
    ctx: typer.Context,
    policy_id: Annotated[int, typer.Argument(help="Policy ID")],
    output: Annotated[
        Path,
        typer.Option("--output", help="Destination file path"),
    ],
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite/--no-overwrite", help="Replace existing file"),
    ] = False,
) -> None:
    """Generate a human-readable PDF for the given policy."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    pdf = client.policies.generate_pdf([{_ID_FIELD: policy_id}])
    write_bytes(output, pdf.encode("utf-8"), overwrite=overwrite)


@policies_app.command(name="import-xacml")
@cli_error_handler
def import_xacml(
    ctx: typer.Context,
    payload_path: Annotated[
        Path | None,
        typer.Option("--payload", help="Path to the XACML policy file"),
    ] = None,
) -> None:
    """Import a XACML policy from a file."""
    if payload_path is None:
        print_error("Missing required option: --payload PATH")
        raise typer.Exit(code=1)
    if not payload_path.is_file():
        print_error(f"Payload file not found: {payload_path}")
        raise typer.Exit(code=1)
    file_bytes = payload_path.read_bytes()
    file_tuple = (payload_path.name, file_bytes, "application/xml")
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    outcome = client.policies.import_xacml(file_tuple)
    render(cli_ctx, outcome, _IMPORT_RESULT_COLUMNS)


@policies_app.command(name="validate-obligations")
@cli_error_handler
def validate_obligations(
    ctx: typer.Context,
    payload_path: Annotated[
        Path | None,
        typer.Option("--payload", help="Path to a JSON payload file"),
    ] = None,
) -> None:
    """Validate an obligation payload before deployment."""
    if payload_path is None:
        print_error("Missing required option: --payload PATH")
        raise typer.Exit(code=1)
    payload = load_payload(payload_path)
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.policies.validate_obligations(payload)
    print_success("Obligations are valid")


@policies_app.command()
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
    """Create a policy from a JSON payload file."""
    reject_data_flag(legacy_data)
    payload = require_payload(payload_path)
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    policy_id = client.policies.create(payload)
    print_success(f"Created policy with ID {policy_id}")


@policies_app.command()
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
    """Modify a policy from a JSON payload file."""
    reject_data_flag(legacy_data)
    payload = require_payload(payload_path)
    cli_ctx: CliContext = ctx.obj
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
    render(
        cli_ctx,
        matches,
        _POLICY_COLUMNS,
        title="Policies",
        wide_columns=_POLICY_WIDE_COLUMNS,
    )


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


def _render_policy_detail(model: BaseModel, console: Console) -> None:
    assert isinstance(model, Policy)
    console.print(f"[bold]Policy[/bold] {model.id}")
    deployment_request_label = (
        None if model.deployment_request is None else str(model.deployment_request.id)
    )
    environment_config_label = (
        None
        if model.environment_config is None
        else (
            f"remote_access={model.environment_config.remote_access}, "
            f"time_since_last_hb_secs="
            f"{model.environment_config.time_since_last_hb_secs}"
        )
    )
    scalar_rows: tuple[tuple[str, object], ...] = (
        ("Name", model.name),
        ("Full Name", model.full_name),
        ("Description", model.description),
        ("Status", model.status),
        ("Category", model.category),
        ("Effect Type", model.effect_type),
        ("Type", model.type),
        ("Folder ID", model.folder_id),
        ("Folder Path", model.folder_path),
        ("Parent ID", model.parent_id),
        ("Parent Name", model.parent_name),
        ("Has Parent", model.has_parent),
        ("Has Sub Policies", model.has_sub_policies),
        ("Has To Subject Components", model.has_to_subject_components),
        ("Has To Resource Components", model.has_to_resource_components),
        ("Environment Config", environment_config_label),
        ("Expression", model.expression),
        ("Sub Policy", model.sub_policy),
        ("Action Type", model.action_type),
        ("Deployed", model.deployed),
        ("Deployment Time", model.deployment_time),
        ("Deployment Pending", model.deployment_pending),
        ("Deployment Request", deployment_request_label),
        ("Manual Deploy", model.manual_deploy),
        ("Revision Count", model.revision_count),
        ("Version", model.version),
        ("Hidden", model.hidden),
        ("Skip Validate", model.skip_validate),
        ("Re-Index Now", model.re_index_now),
        ("Skip Adding True Allow Attribute", model.skip_adding_true_allow_attribute),
        ("Owner ID", model.owner_id),
        ("Owner Display Name", model.owner_display_name),
        ("Created Date", model.created_date),
        ("Last Updated Date", model.last_updated_date),
        ("Modified By ID", model.modified_by_id),
        ("Modified By", model.modified_by),
    )
    count_rows: tuple[tuple[str, int], ...] = (
        ("Tags", len(model.tags)),
        ("Subject Components", len(model.subject_components)),
        ("To Subject Components", len(model.to_subject_components)),
        ("Action Components", len(model.action_components)),
        ("From Resource Components", len(model.from_resource_components)),
        ("To Resource Components", len(model.to_resource_components)),
        ("Allow Obligations", len(model.allow_obligations)),
        ("Deny Obligations", len(model.deny_obligations)),
        ("Sub Policy Refs", len(model.sub_policy_refs)),
        ("Attributes", len(model.attributes)),
        ("Authorities", len(model.authorities)),
        ("Deployment Targets", len(model.deployment_targets)),
        (
            "Component IDs",
            0 if model.component_ids is None else len(model.component_ids),
        ),
    )
    for label, scalar_value in scalar_rows:
        console.print(f"  [bold]{label}[/bold]: {scalar_value}")
    for label, count in count_rows:
        console.print(f"  [bold]{label}[/bold]: {count} defined")


register_detail_renderer(Policy, _render_policy_detail)
