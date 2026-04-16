from __future__ import annotations

import pytest
from pydantic import ValidationError

from nextlabs_sdk._cloudaz._component_models import (
    Authority,
    ComponentCondition,
    ComponentGroupType,
    ComponentStatus,
    DeploymentRequestInfo,
    PolicyModelRef,
)


def test_component_group_type_values() -> None:
    assert ComponentGroupType.SUBJECT.value == "SUBJECT"
    assert ComponentGroupType.RESOURCE.value == "RESOURCE"
    assert ComponentGroupType.ACTION.value == "ACTION"


def test_component_status_values() -> None:
    assert ComponentStatus.DRAFT.value == "DRAFT"
    assert ComponentStatus.APPROVED.value == "APPROVED"
    assert ComponentStatus.OBSOLETE.value == "OBSOLETE"


def test_policy_model_ref_from_api_payload() -> None:
    raw = {"id": 42, "name": "Support Tickets", "shortName": "support_tickets"}
    ref = PolicyModelRef.model_validate(raw)
    assert ref.id == 42
    assert ref.name == "Support Tickets"
    assert ref.short_name == "support_tickets"


def test_policy_model_ref_minimal() -> None:
    raw = {"id": 42}
    ref = PolicyModelRef.model_validate(raw)
    assert ref.id == 42
    assert ref.name is None
    assert ref.short_name is None


def test_policy_model_ref_is_frozen() -> None:
    ref = PolicyModelRef.model_validate({"id": 42})
    with pytest.raises(ValidationError):
        ref.id = 99  # type: ignore[misc]


def test_component_condition_from_api_payload() -> None:
    raw = {
        "attribute": "category",
        "operator": "=",
        "value": "security",
        "rhsType": "CONSTANT",
        "rhsvalue": "security",
    }
    cond = ComponentCondition.model_validate(raw)
    assert cond.attribute == "category"
    assert cond.operator == "="
    assert cond.value == "security"
    assert cond.rhs_type == "CONSTANT"
    assert cond.rhsvalue == "security"


def test_component_condition_minimal() -> None:
    raw = {"attribute": "name", "operator": "!=", "value": "test"}
    cond = ComponentCondition.model_validate(raw)
    assert cond.rhs_type is None
    assert cond.rhsvalue is None


def test_component_condition_is_frozen() -> None:
    cond = ComponentCondition.model_validate(
        {"attribute": "x", "operator": "=", "value": "y"},
    )
    with pytest.raises(ValidationError):
        cond.attribute = "changed"  # type: ignore[misc]


def test_authority_from_api_payload() -> None:
    raw = {"authority": "VIEW_COMPONENT"}
    auth = Authority.model_validate(raw)
    assert auth.authority == "VIEW_COMPONENT"


def test_deployment_request_info_from_api_payload() -> None:
    raw = {
        "id": 200,
        "type": "POLICY",
        "push": False,
        "deploymentTime": 1713172120387,
        "deployDependencies": True,
    }
    dri = DeploymentRequestInfo.model_validate(raw)
    assert dri.id == 200
    assert dri.type == "POLICY"
    assert dri.push is False
    assert dri.deployment_time == 1713172120387
    assert dri.deploy_dependencies is True


def test_deployment_request_info_is_frozen() -> None:
    dri = DeploymentRequestInfo.model_validate(
        {
            "id": 1,
            "type": "COMPONENT",
            "push": True,
            "deploymentTime": 0,
            "deployDependencies": False,
        },
    )
    with pytest.raises(ValidationError):
        dri.id = 99  # type: ignore[misc]
