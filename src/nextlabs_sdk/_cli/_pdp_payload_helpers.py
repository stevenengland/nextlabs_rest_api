"""PDP CLI helpers: build requests, dispatch payloads, format selectors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import typer

from nextlabs_sdk._cli._output import print_error
from nextlabs_sdk._cli._parsing import parse_key_value_attrs
from nextlabs_sdk._pdp import ResourceDimension
from nextlabs_sdk._pdp._payload._format import LoadedPayload, PayloadFormat
from nextlabs_sdk._pdp._request_models import (
    Action,
    Application,
    Environment,
    EvalRequest,
    PermissionsRequest,
    Resource,
    Subject,
)
from nextlabs_sdk.exceptions import PdpPayloadError


@dataclass(frozen=True)
class FlagInputs:
    """Raw request-shaping CLI option values, before validation."""

    subject_id: str | None = None
    resource_id: str | None = None
    resource_type: str | None = None
    action_id: str | None = None
    application_id: str = ""
    subject_attrs: list[str] | None = None
    resource_attrs: list[str] | None = None
    app_attrs: list[str] | None = None
    env_attrs: list[str] | None = None
    resource_dimension: str | None = None
    resource_nocache: bool = False
    return_policy_ids: bool = False
    record_matching_policies: bool = False


def reject_payload_conflicts(flags: FlagInputs) -> None:
    """Raise a Typer error naming any flag that conflicts with ``--payload``."""
    conflicts = _collect_conflicts(flags)
    if conflicts:
        joined = ", ".join(conflicts)
        print_error(
            f"--payload cannot be combined with request-shaping flags; remove: {joined}",
        )
        raise typer.Exit(code=1)


def _collect_conflicts(flags: FlagInputs) -> list[str]:
    checks: list[tuple[str, object]] = [
        ("--subject", flags.subject_id),
        ("--resource", flags.resource_id),
        ("--resource-type", flags.resource_type),
        ("--action", flags.action_id),
        ("--application", flags.application_id),
        ("--subject-attr", flags.subject_attrs),
        ("--resource-attr", flags.resource_attrs),
        ("--app-attr", flags.app_attrs),
        ("--env-attr", flags.env_attrs),
        ("--resource-dimension", flags.resource_dimension),
        ("--resource-nocache", flags.resource_nocache or None),
        ("--return-policy-ids", flags.return_policy_ids or None),
        ("--record-matching-policies", flags.record_matching_policies or None),
    ]
    return [name for name, given in checks if given]


def require_flags(flags: FlagInputs, *, need_action: bool) -> None:
    """Validate required request-shaping flags when ``--payload`` is absent."""
    missing: list[str] = []
    if not flags.subject_id:
        missing.append("--subject")
    if not flags.resource_id:
        missing.append("--resource")
    if not flags.resource_type:
        missing.append("--resource-type")
    if need_action and not flags.action_id:
        missing.append("--action")
    if missing:
        joined = ", ".join(missing)
        print_error(f"Missing required option(s): {joined}")
        raise typer.Exit(code=1)


def parse_dimension(raw: str | None) -> ResourceDimension | None:
    if not raw:
        return None
    try:
        return ResourceDimension(raw)
    except ValueError:
        raise typer.BadParameter(
            f"Invalid resource dimension: {raw}. Must be 'from' or 'to'",
        )


def build_eval_request(flags: FlagInputs) -> EvalRequest:
    return EvalRequest(
        subject=_build_subject(flags),
        resource=_build_resource(flags),
        action=Action(id=flags.action_id or ""),
        application=_build_application(flags),
        environment=_build_environment(flags),
        return_policy_ids=flags.return_policy_ids,
    )


def build_permissions_request(flags: FlagInputs) -> PermissionsRequest:
    return PermissionsRequest(
        subject=_build_subject(flags),
        resource=_build_resource(flags),
        application=_build_application(flags),
        environment=_build_environment(flags),
        return_policy_ids=flags.return_policy_ids,
        record_matching_policies=flags.record_matching_policies,
    )


def _build_subject(flags: FlagInputs) -> Subject:
    return Subject(
        id=flags.subject_id or "",
        attributes=parse_key_value_attrs(flags.subject_attrs or []),
    )


def _build_resource(flags: FlagInputs) -> Resource:
    return Resource(
        id=flags.resource_id or "",
        type=flags.resource_type or "",
        dimension=parse_dimension(flags.resource_dimension),
        nocache=flags.resource_nocache,
        attributes=parse_key_value_attrs(flags.resource_attrs or []),
    )


def _build_application(flags: FlagInputs) -> Application:
    return Application(
        id=flags.application_id,
        attributes=parse_key_value_attrs(flags.app_attrs or []),
    )


def _build_environment(flags: FlagInputs) -> Environment | None:
    if not flags.env_attrs:
        return None
    return Environment(attributes=parse_key_value_attrs(flags.env_attrs))


class _PayloadLoader(Protocol):
    def __call__(
        self,
        source: Path,
        *,
        payload_format: PayloadFormat,
    ) -> LoadedPayload: ...


def run_payload_loader(
    loader: _PayloadLoader,
    path: Path,
    payload_format: PayloadFormat,
) -> LoadedPayload:
    """Invoke ``loader`` translating :class:`PdpPayloadError` into CLI exit."""
    try:
        return loader(path, payload_format=payload_format)
    except PdpPayloadError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from None
