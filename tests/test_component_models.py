from __future__ import annotations

import pytest
from pydantic import ValidationError

from nextlabs_sdk._cloudaz._component_models import (
    Authority,
    Component,
    ComponentCondition,
    ComponentGroupType,
    ComponentStatus,
    DeploymentRequestInfo,
    PolicyModelRef,
)
from nextlabs_sdk._cloudaz._models import TagType


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


def _make_full_component_data() -> dict[str, object]:
    return {
        "id": 101,
        "folderId": None,
        "name": "Security Vulnerabilities",
        "description": "Support Tickets that are categorized as security vulnerabilities.",
        "tags": [
            {
                "id": 21,
                "key": "helpdesk_component",
                "label": "Helpdesk_Component",
                "type": "COMPONENT_TAG",
                "status": "ACTIVE",
            },
        ],
        "type": "RESOURCE",
        "category": "COMPONENT",
        "policyModel": {"id": 42},
        "actions": [],
        "conditions": [
            {
                "attribute": "category",
                "operator": "=",
                "value": "security",
                "rhsType": "CONSTANT",
                "rhsvalue": "security",
            },
        ],
        "memberConditions": [],
        "subComponents": [],
        "status": "DRAFT",
        "parentId": None,
        "parentName": None,
        "deploymentTime": 0,
        "deployed": False,
        "actionType": None,
        "revisionCount": 0,
        "ownerId": 0,
        "ownerDisplayName": "Administrator",
        "createdDate": 1713171640267,
        "modifiedById": 0,
        "modifiedBy": "Administrator",
        "lastUpdatedDate": 1713171640252,
        "skipValidate": False,
        "reIndexAllNow": True,
        "hidden": False,
        "authorities": [{"authority": "VIEW_COMPONENT"}],
        "deploymentRequest": {
            "id": 200,
            "type": "POLICY",
            "push": False,
            "deploymentTime": 1713172120387,
            "deployDependencies": True,
        },
        "folderPath": None,
        "preCreated": False,
        "version": 1,
        "hasInactiveSubComponets": False,
        "deploymentPending": False,
    }


def test_component_from_api_payload() -> None:
    raw = _make_full_component_data()
    comp = Component.model_validate(raw)
    assert comp.id == 101
    assert comp.name == "Security Vulnerabilities"
    assert comp.type == ComponentGroupType.RESOURCE
    assert comp.status == ComponentStatus.DRAFT
    assert comp.category == "COMPONENT"
    assert comp.policy_model is not None
    assert comp.policy_model.id == 42
    assert len(comp.tags) == 1
    assert comp.tags[0].type == TagType.COMPONENT
    assert len(comp.conditions) == 1
    assert comp.conditions[0].attribute == "category"
    assert comp.member_conditions == []
    assert comp.sub_components == []
    assert comp.deployed is False
    assert comp.owner_display_name == "Administrator"
    assert comp.created_date == 1713171640267
    assert comp.deployment_request is not None
    assert comp.deployment_request.deploy_dependencies is True
    assert comp.has_inactive_sub_components is False
    assert comp.version == 1


def test_component_minimal() -> None:
    raw = {
        "id": 1,
        "name": "IT Department",
        "type": "SUBJECT",
        "status": "DRAFT",
    }
    comp = Component.model_validate(raw)
    assert comp.id == 1
    assert comp.type == ComponentGroupType.SUBJECT
    assert comp.folder_id is None
    assert comp.description is None
    assert comp.tags == []
    assert comp.policy_model is None
    assert comp.conditions == []
    assert comp.deployment_request is None
    assert comp.version is None


def test_component_is_frozen() -> None:
    comp = Component.model_validate(_make_full_component_data())
    with pytest.raises(ValidationError):
        comp.name = "changed"  # type: ignore[misc]


def test_component_rejects_invalid_type() -> None:
    with pytest.raises(ValidationError):
        Component.model_validate(
            {"id": 1, "name": "X", "type": "INVALID", "status": "DRAFT"},
        )
