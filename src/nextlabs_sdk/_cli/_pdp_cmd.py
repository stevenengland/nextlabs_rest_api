from __future__ import annotations

from collections.abc import Sequence
from types import MappingProxyType
from typing import Annotated

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._detail_renderers import register_detail_renderer
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import render_json
from nextlabs_sdk._cli._output_format import OutputFormat
from nextlabs_sdk._cli._parsing import parse_key_value_attrs
from nextlabs_sdk._pdp import (
    Action,
    Application,
    ContentType,
    Decision,
    Environment,
    EvalRequest,
    EvalResponse,
    Resource,
)
from nextlabs_sdk._pdp import Obligation, PolicyRef, ResourceDimension, Subject
from nextlabs_sdk._pdp import PermissionsRequest, PermissionsResponse

pdp_app = typer.Typer(help="PDP evaluation commands")

_DECISION_COLORS: MappingProxyType[Decision, str] = MappingProxyType(
    {
        Decision.PERMIT: "green",
        Decision.DENY: "red",
        Decision.NOT_APPLICABLE: "yellow",
        Decision.INDETERMINATE: "dim",
    }
)


def _print_obligations(console: Console, obligations: Sequence[Obligation]) -> None:
    console.print(f"\nObligations ({len(obligations)}):")
    table = Table()
    table.add_column("ID")
    table.add_column("Attribute")
    table.add_column("Value")
    for obl in obligations:
        for attr in obl.attributes:
            table.add_row(obl.id, attr.id, attr.attr_value)
    console.print(table)


def _print_policy_refs(console: Console, refs: Sequence[PolicyRef]) -> None:
    console.print(f"\nMatched Policies ({len(refs)}):")
    table = Table()
    table.add_column("Policy ID")
    table.add_column("Version")
    for ref in refs:
        table.add_row(ref.id, ref.version)
    console.print(table)


def _render_eval_response(response: EvalResponse, console: Console) -> None:
    evaluation = response.first_result
    color = _DECISION_COLORS.get(evaluation.decision, "")
    console.print(f"Decision: [{color}]{evaluation.decision.value}[/{color}]")
    status_msg = evaluation.status.message or evaluation.status.code
    console.print(f"Status:   {status_msg}")
    if evaluation.obligations:
        _print_obligations(console, evaluation.obligations)
    if evaluation.policy_refs:
        _print_policy_refs(console, evaluation.policy_refs)


def _render_eval_detail(model: BaseModel, console: Console) -> None:
    assert isinstance(model, EvalResponse)
    _render_eval_response(model, console)


def _render_permissions_response(
    response: PermissionsResponse, console: Console
) -> None:
    sections = [
        ("Allowed", response.allowed),
        ("Denied", response.denied),
        ("Don't Care", response.dont_care),
    ]
    any_shown = False
    for label, actions in sections:
        if not actions:
            continue
        any_shown = True
        console.print(f"\n{label} ({len(actions)}):")
        table = Table()
        table.add_column("Action")
        table.add_column("Obligations")
        for action_perm in actions:
            table.add_row(action_perm.name, str(len(action_perm.obligations)))
        console.print(table)
    if not any_shown:
        console.print("No action permissions returned.")


def _render_permissions_detail(model: BaseModel, console: Console) -> None:
    assert isinstance(model, PermissionsResponse)
    _render_permissions_response(model, console)


@pdp_app.command(name="eval")
@cli_error_handler
def evaluate(
    ctx: typer.Context,
    subject_id: Annotated[str, typer.Option("--subject", help="Subject ID")],
    resource_id: Annotated[str, typer.Option("--resource", help="Resource ID")],
    resource_type: Annotated[
        str, typer.Option("--resource-type", help="Resource type")
    ],
    action_id: Annotated[str, typer.Option("--action", help="Action name")],
    application_id: Annotated[
        str, typer.Option("--application", help="Application ID")
    ] = "",
    subject_attrs: Annotated[
        list[str] | None,
        typer.Option("--subject-attr", help="Subject attribute (key=value)"),
    ] = None,
    resource_attrs: Annotated[
        list[str] | None,
        typer.Option("--resource-attr", help="Resource attribute (key=value)"),
    ] = None,
    app_attrs: Annotated[
        list[str] | None,
        typer.Option("--app-attr", help="Application attribute (key=value)"),
    ] = None,
    env_attrs: Annotated[
        list[str] | None,
        typer.Option("--env-attr", help="Environment attribute (key=value)"),
    ] = None,
    resource_dimension: Annotated[
        str | None,
        typer.Option("--resource-dimension", help="Resource dimension (from/to)"),
    ] = None,
    resource_nocache: Annotated[
        bool, typer.Option("--resource-nocache", help="Disable resource caching")
    ] = False,
    return_policy_ids: Annotated[
        bool, typer.Option("--return-policy-ids", help="Include matched policy IDs")
    ] = False,
    wire_format: Annotated[
        str, typer.Option("--content-type", help="Wire format (json or xml)")
    ] = "json",
) -> None:
    """Evaluate a PDP policy decision."""
    cli_ctx: CliContext = ctx.obj
    subject = Subject(
        id=subject_id,
        attributes=parse_key_value_attrs(subject_attrs or []),
    )
    dimension = None
    if resource_dimension:
        try:
            dimension = ResourceDimension(resource_dimension)
        except ValueError:
            raise typer.BadParameter(
                f"Invalid resource dimension: {resource_dimension}. "
                f"Must be 'from' or 'to'",
            )
    resource = Resource(
        id=resource_id,
        type=resource_type,
        dimension=dimension,
        nocache=resource_nocache,
        attributes=parse_key_value_attrs(resource_attrs or []),
    )
    application = Application(
        id=application_id,
        attributes=parse_key_value_attrs(app_attrs or []),
    )
    environment = (
        Environment(attributes=parse_key_value_attrs(env_attrs)) if env_attrs else None
    )
    ct_enum = ContentType.XML if wire_format == "xml" else ContentType.JSON
    request = EvalRequest(
        subject=subject,
        resource=resource,
        action=Action(id=action_id),
        application=application,
        environment=environment,
        return_policy_ids=return_policy_ids,
    )
    client = _client_factory.make_pdp_client(cli_ctx)
    response = client.evaluate(request, content_type=ct_enum)
    if cli_ctx.output_format is OutputFormat.JSON:
        render_json(response)
    else:
        _render_eval_response(response, Console())


@pdp_app.command()
@cli_error_handler
def permissions(
    ctx: typer.Context,
    subject_id: Annotated[str, typer.Option("--subject", help="Subject ID")],
    resource_id: Annotated[str, typer.Option("--resource", help="Resource ID")],
    resource_type: Annotated[
        str, typer.Option("--resource-type", help="Resource type")
    ],
    application_id: Annotated[
        str, typer.Option("--application", help="Application ID")
    ] = "",
    subject_attrs: Annotated[
        list[str] | None,
        typer.Option("--subject-attr", help="Subject attribute (key=value)"),
    ] = None,
    resource_attrs: Annotated[
        list[str] | None,
        typer.Option("--resource-attr", help="Resource attribute (key=value)"),
    ] = None,
    app_attrs: Annotated[
        list[str] | None,
        typer.Option("--app-attr", help="Application attribute (key=value)"),
    ] = None,
    env_attrs: Annotated[
        list[str] | None,
        typer.Option("--env-attr", help="Environment attribute (key=value)"),
    ] = None,
    resource_dimension: Annotated[
        str | None,
        typer.Option("--resource-dimension", help="Resource dimension (from/to)"),
    ] = None,
    resource_nocache: Annotated[
        bool, typer.Option("--resource-nocache", help="Disable resource caching")
    ] = False,
    return_policy_ids: Annotated[
        bool, typer.Option("--return-policy-ids", help="Include matched policy IDs")
    ] = False,
    record_matching_policies: Annotated[
        bool,
        typer.Option("--record-matching-policies", help="Record matching policies"),
    ] = False,
    wire_format: Annotated[
        str, typer.Option("--content-type", help="Wire format (json or xml)")
    ] = "json",
) -> None:
    """Get allowed and denied actions for a subject-resource pair."""
    cli_ctx: CliContext = ctx.obj
    subject = Subject(
        id=subject_id,
        attributes=parse_key_value_attrs(subject_attrs or []),
    )
    dimension = None
    if resource_dimension:
        try:
            dimension = ResourceDimension(resource_dimension)
        except ValueError:
            raise typer.BadParameter(
                f"Invalid resource dimension: {resource_dimension}. "
                f"Must be 'from' or 'to'",
            )
    resource = Resource(
        id=resource_id,
        type=resource_type,
        dimension=dimension,
        nocache=resource_nocache,
        attributes=parse_key_value_attrs(resource_attrs or []),
    )
    application = Application(
        id=application_id,
        attributes=parse_key_value_attrs(app_attrs or []),
    )
    environment = (
        Environment(attributes=parse_key_value_attrs(env_attrs)) if env_attrs else None
    )
    ct_enum = ContentType.XML if wire_format == "xml" else ContentType.JSON
    request = PermissionsRequest(
        subject=subject,
        resource=resource,
        application=application,
        environment=environment,
        return_policy_ids=return_policy_ids,
        record_matching_policies=record_matching_policies,
    )
    client = _client_factory.make_pdp_client(cli_ctx)
    response = client.permissions(request, content_type=ct_enum)
    if cli_ctx.output_format is OutputFormat.JSON:
        render_json(response)
    else:
        _render_permissions_response(response, Console())


register_detail_renderer(EvalResponse, _render_eval_detail)
register_detail_renderer(PermissionsResponse, _render_permissions_detail)
