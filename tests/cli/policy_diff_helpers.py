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
    return PolicyHistoryEntry(id=10, revision=revision, action_type=action_type)


def revision(
    number: int,
    description: str = "d",
    deployment_time: int = 0,
    effect_type: str = "ALLOW",
) -> PolicyRevision:
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
    return {"id": component_id, "name": name, "version": version, "subComponents": []}


def revision_with_subjects(
    number: int, components: list[dict[str, Any]]
) -> PolicyRevision:
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
    return {"id": None, "policyModelId": 0, "name": name, "params": params}


def revision_with_obligations(
    number: int, obligations: list[dict[str, Any]], *, deny: bool = False
) -> PolicyRevision:
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
    return {"operator": operator, "components": list(components)}


def cross_revision(
    policy_id: int,
    name: str,
    number: int,
    description: str = "d",
    components: list[dict[str, Any]] | None = None,
) -> PolicyRevision:
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
