from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
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
from nextlabs_sdk._cli._pdp_payload_helpers import (
    FlagInputs,
    build_eval_request,
    build_permissions_request,
    reject_payload_conflicts,
    require_flags,
    run_payload_loader,
)
from nextlabs_sdk._pdp import (
    ContentType,
    Decision,
    EvalRequest,
    EvalResponse,
    Obligation,
    PermissionsRequest,
    PermissionsResponse,
    PolicyRef,
)
from nextlabs_sdk._pdp._client import PdpClient
from nextlabs_sdk._pdp._payload._format import LoadedPayload, PayloadFormat
from nextlabs_sdk._pdp._payload._loader import (
    load_eval_payload,
    load_permissions_payload,
)

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
    console.print(f"Status:   {status_msg}", markup=False, highlight=False)
    if evaluation.status.detail:
        console.print(
            f"Detail:   {evaluation.status.detail}",
            markup=False,
            highlight=False,
        )
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


def _resolve_content_type(wire_format: str) -> ContentType:
    return ContentType.XML if wire_format == "xml" else ContentType.JSON


def _emit_eval(
    response: EvalResponse,
    output_format: OutputFormat,
) -> None:
    if output_format is OutputFormat.JSON:
        render_json(response)
    else:
        _render_eval_response(response, Console())


def _emit_permissions(
    response: PermissionsResponse,
    output_format: OutputFormat,
) -> None:
    if output_format is OutputFormat.JSON:
        render_json(response)
    else:
        _render_permissions_response(response, Console())


def _dispatch_eval_payload(
    client: PdpClient,
    loaded: LoadedPayload,
    content_type: ContentType,
) -> EvalResponse:
    if loaded.kind == "raw_xacml":
        assert loaded.body is not None
        return client.evaluate_raw(loaded.body, content_type=content_type)
    assert isinstance(loaded.request, EvalRequest)
    return client.evaluate(loaded.request, content_type=content_type)


def _dispatch_permissions_payload(
    client: PdpClient,
    loaded: LoadedPayload,
    content_type: ContentType,
) -> PermissionsResponse:
    if loaded.kind == "raw_xacml":
        assert loaded.body is not None
        return client.permissions_raw(loaded.body, content_type=content_type)
    assert isinstance(loaded.request, PermissionsRequest)
    return client.permissions(loaded.request, content_type=content_type)


@pdp_app.command(name="eval")
@cli_error_handler
def evaluate(
    ctx: typer.Context,
    payload_path: Annotated[
        Path | None,
        typer.Option(
            "--payload",
            help="Path to a YAML / JSON / raw XACML JSON request file.",
        ),
    ] = None,
    payload_format: Annotated[
        PayloadFormat,
        typer.Option(
            "--payload-format",
            help="Force payload format (auto, yaml, json, xacml).",
            case_sensitive=False,
        ),
    ] = PayloadFormat.AUTO,
    subject_id: Annotated[
        str | None, typer.Option("--subject", help="Subject ID")
    ] = None,
    resource_id: Annotated[
        str | None, typer.Option("--resource", help="Resource ID")
    ] = None,
    resource_type: Annotated[
        str | None, typer.Option("--resource-type", help="Resource type")
    ] = None,
    action_id: Annotated[
        str | None, typer.Option("--action", help="Action name")
    ] = None,
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
    flags = FlagInputs(
        subject_id=subject_id,
        resource_id=resource_id,
        resource_type=resource_type,
        action_id=action_id,
        application_id=application_id,
        subject_attrs=subject_attrs,
        resource_attrs=resource_attrs,
        app_attrs=app_attrs,
        env_attrs=env_attrs,
        resource_dimension=resource_dimension,
        resource_nocache=resource_nocache,
        return_policy_ids=return_policy_ids,
    )
    content_type = _resolve_content_type(wire_format)
    client = _client_factory.make_pdp_client(cli_ctx)

    if payload_path is None:
        require_flags(flags, need_action=True)
        request = build_eval_request(flags)
        response = client.evaluate(request, content_type=content_type)
    else:
        reject_payload_conflicts(flags)
        loaded = run_payload_loader(load_eval_payload, payload_path, payload_format)
        assert isinstance(loaded, LoadedPayload)
        response = _dispatch_eval_payload(client, loaded, content_type)

    _emit_eval(response, cli_ctx.output_format)


@pdp_app.command()
@cli_error_handler
def permissions(
    ctx: typer.Context,
    payload_path: Annotated[
        Path | None,
        typer.Option(
            "--payload",
            help="Path to a YAML / JSON / raw XACML JSON request file.",
        ),
    ] = None,
    payload_format: Annotated[
        PayloadFormat,
        typer.Option(
            "--payload-format",
            help="Force payload format (auto, yaml, json, xacml).",
            case_sensitive=False,
        ),
    ] = PayloadFormat.AUTO,
    subject_id: Annotated[
        str | None, typer.Option("--subject", help="Subject ID")
    ] = None,
    resource_id: Annotated[
        str | None, typer.Option("--resource", help="Resource ID")
    ] = None,
    resource_type: Annotated[
        str | None, typer.Option("--resource-type", help="Resource type")
    ] = None,
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
    flags = FlagInputs(
        subject_id=subject_id,
        resource_id=resource_id,
        resource_type=resource_type,
        application_id=application_id,
        subject_attrs=subject_attrs,
        resource_attrs=resource_attrs,
        app_attrs=app_attrs,
        env_attrs=env_attrs,
        resource_dimension=resource_dimension,
        resource_nocache=resource_nocache,
        return_policy_ids=return_policy_ids,
        record_matching_policies=record_matching_policies,
    )
    content_type = _resolve_content_type(wire_format)
    client = _client_factory.make_pdp_client(cli_ctx)

    if payload_path is None:
        require_flags(flags, need_action=False)
        request = build_permissions_request(flags)
        response = client.permissions(request, content_type=content_type)
    else:
        reject_payload_conflicts(flags)
        loaded = run_payload_loader(
            load_permissions_payload,
            payload_path,
            payload_format,
        )
        assert isinstance(loaded, LoadedPayload)
        response = _dispatch_permissions_payload(client, loaded, content_type)

    _emit_permissions(response, cli_ctx.output_format)


register_detail_renderer(EvalResponse, _render_eval_detail)
register_detail_renderer(PermissionsResponse, _render_permissions_detail)
