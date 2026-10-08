"""Shared raw payloads and serialization paths for membership regressions."""

from __future__ import annotations

from typing import Any

from nextlabs_sdk.cloudaz import Component, ComponentRevision, Policy, PolicyRevision


def composite_component_data(
    operator: str,
    members: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a composite component with caller-supplied raw members."""
    if members is None:
        members = [{"id": 87, "name": "Member", "notFound": False}]
    return {
        "id": 101,
        "name": "Composite",
        "type": "SUBJECT",
        "status": "DRAFT",
        "memberConditions": [{"operator": operator, "members": members}],
    }


def composite_policy_data(
    operator: str,
    members: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a policy embedding a composite subject component."""
    component = {
        "id": 42,
        "memberConditions": composite_component_data(operator, members)[
            "memberConditions"
        ],
    }
    return {
        "id": 82,
        "name": "Policy",
        "status": "DRAFT",
        "effectType": "ALLOW",
        "subjectComponents": [{"operator": "IN", "components": [component]}],
    }


def dump_member_condition(
    model: Component | ComponentRevision | Policy | PolicyRevision,
) -> dict[str, Any]:
    """Extract the first condition from alias-based JSON serialization."""
    serialized = model.model_dump(by_alias=True, mode="json")
    if isinstance(model, ComponentRevision):
        serialized = serialized["componentDetail"]
    elif isinstance(model, PolicyRevision):
        serialized = serialized["policyDetail"]
    if isinstance(model, (Policy, PolicyRevision)):
        serialized = serialized["subjectComponents"][0]["components"][0]
    return serialized["memberConditions"][0]
