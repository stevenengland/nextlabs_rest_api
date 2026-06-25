from __future__ import annotations

import json
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
from nextlabs_sdk._cli._diff import (
    _engine,
    _format,
    _models,
    _render_semantic,
    _render_unified,
)
from nextlabs_sdk._cli._diff._revision_select import (
    InsufficientRevisionsError,
    UnknownRevisionError,
    select_policy_revision,
    select_revisions,
)
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._factory import make_group
from nextlabs_sdk._cli._output import ColumnDef, print_error, print_success, render
from nextlabs_sdk._cli._output_format import OutputFormat
from nextlabs_sdk._cli._payload_loader import (
    load_payload,
    reject_data_flag,
    require_payload,
)
from nextlabs_sdk._cloudaz._policies import PolicyService
from nextlabs_sdk._cloudaz._policy_models import Policy, PolicyRevision
from nextlabs_sdk._cloudaz._search import SearchCriteria, SortOrder
from nextlabs_sdk._cloudaz._search.field_expr import parse_field_expr
from nextlabs_sdk._cloudaz._search.where import transpile_where
from nextlabs_sdk.exceptions import SearchExpressionError

policies_app = make_group("Policy management commands")

_UTF8 = "utf-8"

_ID_FIELD = "id"
_ID_COLUMN = ColumnDef("ID", _ID_FIELD)
_NAME_COLUMN = ColumnDef("Name", "name")

_POLICY_COLUMNS = (
    _ID_COLUMN,
    _NAME_COLUMN,
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
    _NAME_COLUMN,
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

_HISTORY_COLUMNS = (
    ColumnDef("Revision", "revision"),
    ColumnDef("Action", "action_type"),
    ColumnDef("Created By", "created_by"),
    ColumnDef("Modified By", "modified_by"),
    ColumnDef("Active From", "active_from"),
    ColumnDef("Active To", "active_to"),
)

_HISTORY_WIDE_COLUMNS: tuple[ColumnDef, ...] = (
    _ID_COLUMN,
    ColumnDef("Submitted By", "submitted_by"),
    ColumnDef("Submitted Date", "submitted_date"),
)

_REVISION_COLUMNS = (
    _ID_COLUMN,
    ColumnDef("Revision", "revision"),
    _NAME_COLUMN,
    ColumnDef("Action", "action_type"),
    ColumnDef("Created By", "created_by"),
    ColumnDef("Modified By", "modified_by"),
)


@policies_app.command()
@cli_error_handler
def get(
    ctx: typer.Context,
    policy_id: Annotated[int, typer.Argument(help="Policy ID")],  # noqa: WPS204
) -> None:
    """Get a policy by ID."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)  # noqa: WPS204
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


@policies_app.command()
@cli_error_handler
def history(
    ctx: typer.Context,
    policy_id: Annotated[int, typer.Argument(help="Policy ID")],
) -> None:
    """List the revision history of a policy."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    entries = client.policies.list_history(policy_id)
    render(
        cli_ctx,
        entries,
        _HISTORY_COLUMNS,
        title="Policy History",
        wide_columns=_HISTORY_WIDE_COLUMNS,
    )


@policies_app.command(name="view-revision")
@cli_error_handler
def view_revision(
    ctx: typer.Context,
    revision_id: Annotated[int, typer.Argument(help="Revision ID")],
    revision: Annotated[int, typer.Argument(help="Revision number")] = 0,
) -> None:
    """View a specific revision of a policy."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    rev = client.policies.get_revision(revision_id, revision)
    render(cli_ctx, rev, _REVISION_COLUMNS)


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
    write_bytes(output, exported.encode(_UTF8), overwrite=overwrite)


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
    write_bytes(output, xacml.encode(_UTF8), overwrite=overwrite)


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
    write_bytes(output, pdf.encode(_UTF8), overwrite=overwrite)


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
def search(  # noqa: WPS211
    ctx: typer.Context,
    status: Annotated[
        str | None, typer.Option(help="Filter by status (DRAFT, APPROVED)")
    ] = None,
    effect: Annotated[
        str | None, typer.Option(help="Filter by effect type (ALLOW, DENY)")
    ] = None,
    text: Annotated[str | None, typer.Option(help="Text search")] = None,
    tag: Annotated[str | None, typer.Option(help="Filter by tag key")] = None,
    field: Annotated[
        list[str] | None,
        typer.Option(
            "--field",
            help="Repeatable NAME[:TYPE]=VALUE field expression",
        ),
    ] = None,
    where: Annotated[
        str | None,
        typer.Option(
            "--where",
            help="SCIM filter, e.g. 'status eq \"DRAFT\"'",
        ),
    ] = None,
    criteria_file: Annotated[
        Path | None,
        typer.Option(
            "--criteria-file",
            help=(
                "Path to a JSON SearchCriteria posted verbatim; "
                "mutually exclusive with the expression flags"
            ),
        ),
    ] = None,
    sort: Annotated[
        list[str] | None,
        typer.Option(
            "--sort",
            help="Repeatable sort field[:asc|desc] (default desc)",
        ),
    ] = None,
    page_no: Annotated[
        int | None, typer.Option("--page-no", help="Page number (default 0)")
    ] = None,
    page_size: Annotated[
        int | None, typer.Option(help="Results per page (default 20)")
    ] = None,
) -> None:
    """Search policies."""
    cli_ctx: CliContext = ctx.obj
    criteria = _build_search_criteria(
        status=status,
        effect=effect,
        text=text,
        tag=tag,
        field=field,
        where=where,
        criteria_file=criteria_file,
        sort=sort,
        page_no=page_no,
        page_size=page_size,
    )
    client = _client_factory.make_cloudaz_client(cli_ctx)
    matches = list(client.policy_search.search(criteria))
    render(
        cli_ctx,
        matches,
        _POLICY_COLUMNS,
        title="Policies",
        wide_columns=_POLICY_WIDE_COLUMNS,
    )


_EXPRESSION_FLAGS = ("--status", "--effect", "--text", "--tag", "--field", "--where")
_DEFAULT_PAGE_NO = 0
_DEFAULT_PAGE_SIZE = 20


def _build_search_criteria(  # noqa: WPS211
    *,
    status: str | None,
    effect: str | None,
    text: str | None,
    tag: str | None,
    field: list[str] | None,
    where: str | None,
    criteria_file: Path | None,
    sort: list[str] | None,
    page_no: int | None,
    page_size: int | None,
) -> SearchCriteria:
    if criteria_file is not None:
        _reject_expression_flags([status, effect, text, tag, field, where])
        _reject_sort_and_paging(sort=sort, page_no=page_no, page_size=page_size)
        return SearchCriteria.from_payload(_load_criteria_file(criteria_file))
    criteria = SearchCriteria()
    _apply_shorthands(criteria, status=status, effect=effect, text=text, tag=tag)
    for field_expr in field or []:
        criteria.filter_field(parse_field_expr(field_expr))
    _apply_where(criteria, where)
    for sort_spec in sort or []:
        sort_field, sort_order = _parse_sort(sort_spec)
        criteria.sort_by(sort_field, sort_order)
    criteria.page(
        page_no=_DEFAULT_PAGE_NO if page_no is None else page_no,
        page_size=_DEFAULT_PAGE_SIZE if page_size is None else page_size,
    )
    return criteria


def _reject_expression_flags(flag_values: list[object]) -> None:
    provided = [flag for flag, is_set in zip(_EXPRESSION_FLAGS, flag_values) if is_set]
    if provided:
        joined = ", ".join(provided)
        raise SearchExpressionError(
            f"--criteria-file cannot be combined with {joined}",
        )


def _reject_sort_and_paging(
    *,
    sort: list[str] | None,
    page_no: int | None,
    page_size: int | None,
) -> None:
    provided = []
    if sort:
        provided.append("--sort")
    if page_no is not None:
        provided.append("--page-no")
    if page_size is not None:
        provided.append("--page-size")
    if provided:
        joined = ", ".join(provided)
        raise SearchExpressionError(
            f"--criteria-file cannot be combined with {joined}",
        )


def _load_criteria_file(criteria_file: Path) -> dict[str, object]:
    try:
        payload = json.loads(criteria_file.read_text(encoding=_UTF8))
    except (OSError, json.JSONDecodeError) as exc:
        raise SearchExpressionError(
            f"could not read criteria file {criteria_file}: {exc}",
        ) from exc
    if not isinstance(payload, dict):
        raise SearchExpressionError(
            f"criteria file {criteria_file} must contain a JSON object",
        )
    return payload


def _parse_sort(sort_spec: str) -> tuple[str, SortOrder]:
    field_name, _, order_token = sort_spec.partition(":")
    if not order_token:
        return field_name, SortOrder.DESC
    try:
        return field_name, SortOrder[order_token.upper()]
    except KeyError as exc:
        raise SearchExpressionError(
            f"invalid sort order {order_token!r}; use 'asc' or 'desc'",
        ) from exc


def _apply_shorthands(
    criteria: SearchCriteria,
    *,
    status: str | None,
    effect: str | None,
    text: str | None,
    tag: str | None,
) -> None:
    if status:
        criteria.filter_status(status)
    if effect:
        criteria.filter_effect_type(effect)
    if text:
        criteria.filter_text(text)
    if tag:
        criteria.filter_tags(tag)


def _apply_where(criteria: SearchCriteria, where: str | None) -> None:
    if not where:
        return
    for where_field in transpile_where(where):
        criteria.filter_field(where_field)


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


@policies_app.command()
@cli_error_handler
def diff(  # noqa: WPS211
    ctx: typer.Context,
    policy_id: Annotated[int, typer.Argument(help="Policy ID")],
    policy_id_b: Annotated[
        int | None,
        typer.Argument(help="Second policy ID; when given, compares the two policies"),
    ] = None,
    from_rev: Annotated[
        int | None, typer.Option("--from", help="Override the 'from' revision")
    ] = None,
    to_rev: Annotated[
        int | None, typer.Option("--to", help="Override the 'to' revision")
    ] = None,
    show_all: Annotated[
        bool, typer.Option("--show-all", help="Reveal ordering + noise differences")
    ] = False,
    diff_format: Annotated[
        _format.DiffFormat,
        typer.Option("--format", help="Human renderer: semantic (default) or unified"),
    ] = _format.DiffFormat.SEMANTIC,
    exit_code: Annotated[
        bool,
        typer.Option(
            "--exit-code",
            help="Exit non-zero when post-filter differences exist (default 0)",
        ),
    ] = False,
) -> None:
    """Show a diff between two revisions of a policy, or between two policies.

    With one policy id, compares two revisions of that policy. With a second
    policy id, compares each policy's latest revision (``--from`` selects the
    first policy's revision, ``--to`` the second's), ignoring top-level identity
    fields.
    """
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    cross_policy = policy_id_b is not None
    try:
        old, new = _resolve_diff_revisions(
            client.policies,
            policy_id,
            policy_id_b,
            from_rev=from_rev,
            to_rev=to_rev,
        )
    except (InsufficientRevisionsError, UnknownRevisionError) as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from exc
    old_payload = old.policy_detail.model_dump(mode="json", by_alias=True)
    new_payload = new.policy_detail.model_dump(mode="json", by_alias=True)
    diff_result = _engine.diff_payloads(
        old_payload, new_payload, show_all=show_all, cross_policy=cross_policy
    )
    header = _build_diff_header(old, new, cross_policy=cross_policy)
    if cli_ctx.output_format is OutputFormat.JSON:
        print(json.dumps(_models.diff_result_to_dict(diff_result), indent=2))
    elif diff_format is _format.DiffFormat.UNIFIED:
        _render_unified.render_unified(
            _render_unified.UnifiedDiffInput(
                old=old_payload,
                new=new_payload,
                header=header,
                diff_result=diff_result,
            ),
            show_all=show_all,
        )
    else:
        _render_semantic.render_semantic(diff_result, header, show_all=show_all)
    if exit_code and diff_result.changes:
        raise typer.Exit(code=1)


def _resolve_diff_revisions(
    policies: PolicyService,
    policy_id: int,
    policy_id_b: int | None,
    *,
    from_rev: int | None,
    to_rev: int | None,
) -> tuple[PolicyRevision, PolicyRevision]:
    if policy_id_b is None:
        return select_revisions(policies, policy_id, from_rev=from_rev, to_rev=to_rev)
    old = select_policy_revision(policies, policy_id, revision=from_rev)
    new = select_policy_revision(policies, policy_id_b, revision=to_rev)
    return old, new


def _build_diff_header(
    old: PolicyRevision, new: PolicyRevision, *, cross_policy: bool
) -> _models.DiffHeader:
    if cross_policy:
        return _models.DiffHeader(
            policy_name=old.policy_detail.name,
            policy_id=old.policy_detail.id,
            from_rev=old.revision,
            to_rev=new.revision,
            to_policy_name=new.policy_detail.name,
            to_policy_id=new.policy_detail.id,
        )
    return _models.DiffHeader(
        policy_name=new.policy_detail.name,
        policy_id=new.policy_detail.id,
        from_rev=old.revision,
        to_rev=new.revision,
    )
