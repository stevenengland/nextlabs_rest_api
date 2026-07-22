"""Shared fixtures and revision factories for the policies-diff CLI tests.

The ``test_cli_policy_diff_*`` modules each exercise one behavior area of
``policies diff`` (semantic/unified report, JSON delta, exit-code, element
changes, cross-policy). They share the same CloudAz client stub wiring and
the same ``PolicyRevision`` builders, collected here so a change to the
request shape or stub surface is made once.
"""

from __future__ import annotations

from typing import Any

from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk.cloudaz import (
    CloudAzClient,
    Policy,
    PolicyHistoryEntry,
    PolicyRevision,
    PolicyService,
    Tag,
)

runner = CliRunner()

GLOBAL_OPTS = (
    "--base-url",
    "https://example.com",
    "--username",
    "admin",
    "--password",
    "secret",
)


def make_stub() -> tuple[Any, Any]:
    """Stub ``make_cloudaz_client`` and return the (client, policies) mocks."""
    mock_client = mock(CloudAzClient)
    mock_policies = mock(PolicyService)
    mock_client.policies = mock_policies
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)
    return mock_client, mock_policies


def entry(revision: int, action_type: str = "DE") -> PolicyHistoryEntry:
    """Build a minimal policy revision-history entry.

    Args:
        revision: The revision number to record.
        action_type: The history action code (e.g. ``"DE"`` for deploy).

    Returns:
        A ``PolicyHistoryEntry`` for policy id 10 at the given revision.
    """
    return PolicyHistoryEntry(id=10, revision=revision, action_type=action_type)


def revision(
    number: int,
    description: str = "d",
    deployment_time: int = 0,
    effect_type: str = "ALLOW",
) -> PolicyRevision:
    """Build a policy revision with a bare-bones policy body.

    Args:
        number: The revision number.
        description: The policy description.
        deployment_time: The policy's deployment timestamp.
        effect_type: The policy's effect type (e.g. ``"ALLOW"``/``"DENY"``).

    Returns:
        A ``PolicyRevision`` for policy id 82 at the given revision.
    """
    return PolicyRevision(
        id=10,
        revision=number,
        action_type="DE",
        policy_detail=Policy(
            id=82,
            name="P",
            status="DRAFT",
            effect_type=effect_type,
            description=description,
            deployment_time=deployment_time,
        ),
    )


def component(component_id: int, name: str, version: int = 1) -> dict[str, Any]:
    """Build a raw component payload with no sub-components.

    Args:
        component_id: The component's id.
        name: The component's name.
        version: The component's version.

    Returns:
        A component dict shaped for inclusion in a ``ComponentGroup``.
    """
    return {"id": component_id, "name": name, "version": version, "subComponents": []}


def revision_with_subjects(
    number: int, components: list[dict[str, Any]]
) -> PolicyRevision:
    """Build a policy revision with a single AND-grouped subject component group.

    Args:
        number: The revision number.
        components: The raw component payloads to group under the subjects.

    Returns:
        A ``PolicyRevision`` for policy id 82 at the given revision.
    """
    policy = Policy.model_validate(
        {
            "id": 82,
            "name": "P",
            "status": "DRAFT",
            "effectType": "ALLOW",
            "subjectComponents": [{"operator": "AND", "components": components}],
        }
    )
    return PolicyRevision(
        id=10, revision=number, action_type="DE", policy_detail=policy
    )


def revision_with_subject_groups(
    number: int, groups: list[dict[str, Any]]
) -> PolicyRevision:
    """Build a policy revision with caller-supplied subject component groups.

    Args:
        number: The revision number.
        groups: The raw subject component groups (already operator-wrapped).

    Returns:
        A ``PolicyRevision`` for policy id 82 at the given revision.
    """
    policy = Policy.model_validate(
        {
            "id": 82,
            "name": "P",
            "status": "DRAFT",
            "effectType": "ALLOW",
            "subjectComponents": groups,
        }
    )
    return PolicyRevision(
        id=10, revision=number, action_type="DE", policy_detail=policy
    )


def obligation(name: str, params: dict[str, str]) -> dict[str, Any]:
    """Build a raw policy obligation payload.

    Args:
        name: The obligation's name.
        params: The obligation's parameter map.

    Returns:
        An obligation dict shaped for inclusion in a policy's
        ``allowObligations``/``denyObligations`` list.
    """
    return {"id": None, "policyModelId": 0, "name": name, "params": params}


def revision_with_obligations(
    number: int, obligations: list[dict[str, Any]], *, deny: bool = False
) -> PolicyRevision:
    """Build a policy revision with allow- or deny-side obligations.

    Args:
        number: The revision number.
        obligations: The raw obligation payloads to attach.
        deny: When ``True``, attach to ``denyObligations`` instead of
            ``allowObligations``.

    Returns:
        A ``PolicyRevision`` for policy id 82 at the given revision.
    """
    field = "denyObligations" if deny else "allowObligations"
    policy = Policy.model_validate(
        {
            "id": 82,
            "name": "P",
            "status": "DRAFT",
            "effectType": "ALLOW",
            field: obligations,
        }
    )
    return PolicyRevision(
        id=10, revision=number, action_type="DE", policy_detail=policy
    )


def revision_with_tags(number: int, tags: list[Tag]) -> PolicyRevision:
    """Build a policy revision carrying the given tags.

    Args:
        number: The revision number.
        tags: The tags to attach to the policy.

    Returns:
        A ``PolicyRevision`` for policy id 82 at the given revision.
    """
    return PolicyRevision(
        id=10,
        revision=number,
        action_type="DE",
        policy_detail=Policy(
            id=82,
            name="P",
            status="DRAFT",
            effect_type="ALLOW",
            tags=tags,
        ),
    )


def grouped(operator: str, *components: dict[str, Any]) -> dict[str, Any]:
    """Wrap raw component payloads into an operator-grouped component group.

    Args:
        operator: The boolean operator joining the components (e.g. ``"AND"``).
        *components: The raw component payloads to group.

    Returns:
        A component-group dict with the given operator and components.
    """
    return {"operator": operator, "components": list(components)}


def cross_revision(
    policy_id: int,
    name: str,
    number: int,
    description: str = "d",
    components: list[dict[str, Any]] | None = None,
) -> PolicyRevision:
    """Build a policy revision for a caller-chosen policy id (cross-policy diffs).

    Args:
        policy_id: The policy id to build the revision for.
        name: The policy's name.
        number: The revision number.
        description: The policy description.
        components: When given, wrapped in an AND-grouped subject component
            group and attached to the policy.

    Returns:
        A ``PolicyRevision`` for the given policy id at the given revision.
    """
    payload: dict[str, Any] = {
        "id": policy_id,
        "name": name,
        "status": "DRAFT",
        "effectType": "ALLOW",
        "description": description,
    }
    if components is not None:
        payload["subjectComponents"] = [{"operator": "AND", "components": components}]
    return PolicyRevision(
        id=policy_id * 10,
        revision=number,
        action_type="DE",
        policy_detail=Policy.model_validate(payload),
    )
