from __future__ import annotations

import pytest
from pydantic import ValidationError

from nextlabs_sdk._cloudaz._component_models import (
    Authority,
    ComponentCondition,
    ComponentGroupType,
    ComponentNameData,
    ComponentNameEntry,
    ComponentStatus,
    Dependency,
    DeploymentRequestInfo,
    DeploymentResult,
    PolicyModelRef,
    PredicateAttribute,
    PredicateData,
    PushResult,
)
from nextlabs_sdk.cloudaz import Component, ComponentLite, TagType


def _deployment_request_data() -> dict[str, object]:
    return {
        "id": 1,
        "type": "COMPONENT",
        "push": True,
        "deploymentTime": 0,
        "deployDependencies": False,
    }


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


def _make_component_lite_data() -> dict[str, object]:
    return {
        "id": 101,
        "folderId": -1,
        "folderPath": None,
        "name": "Security Vulnerabilities",
        "lowercase_name": "security vulnerabilities",
        "fullName": "RESOURCE/Security Vulnerabilities",
        "description": "Tickets categorized as security vulnerabilities.",
        "status": "APPROVED",
        "modelId": 42,
        "modelType": "Support Tickets",
        "group": "RESOURCE",
        "lastUpdatedDate": 1713173211329,
        "createdDate": 1713171640267,
        "ownerId": 0,
        "ownerDisplayName": "Administrator",
        "modifiedById": 0,
        "modifiedBy": "Administrator",
        "hasIncludedIn": False,
        "hasSubComponents": False,
        "predicateData": {
            "operator": None,
            "referenceIds": [],
            "attributes": [{"lhs": "category", "operator": "=", "rhs": "security"}],
            "actions": [],
        },
        "tags": [
            {
                "id": 21,
                "key": "helpdesk_component",
                "label": "Helpdesk_Component",
                "type": "COMPONENT_TAG",
                "status": "ACTIVE",
            },
        ],
        "includedInComponents": [],
        "subComponents": [],
        "deploymentTime": 1713173211332,
        "deployed": True,
        "actionType": "DE",
        "revisionCount": 1,
        "empty": False,
        "version": 2,
        "authorities": [{"authority": "VIEW_COMPONENT"}],
        "preCreated": False,
        "referedInPolicies": False,
        "deploymentPending": False,
    }


@pytest.mark.parametrize(
    "enum_cls,expected",
    [
        pytest.param(
            ComponentGroupType,
            {"SUBJECT": "SUBJECT", "RESOURCE": "RESOURCE", "ACTION": "ACTION"},
            id="component-group-type",
        ),
        pytest.param(
            ComponentStatus,
            {"DRAFT": "DRAFT", "APPROVED": "APPROVED", "OBSOLETE": "OBSOLETE"},
            id="component-status",
        ),
    ],
)
def test_enum_values(enum_cls, expected):
    for name, value in expected.items():
        assert enum_cls[name].value == value


@pytest.mark.parametrize(
    "model,data,field,new_value",
    [
        pytest.param(PolicyModelRef, {"id": 42}, "id", 99, id="policy-model-ref"),
        pytest.param(
            ComponentCondition,
            {"attribute": "x", "operator": "=", "value": "y"},
            "attribute",
            "changed",
            id="component-condition",
        ),
        pytest.param(
            DeploymentRequestInfo,
            _deployment_request_data(),
            "id",
            99,
            id="deployment-request-info",
        ),
        pytest.param(Component, None, "name", "changed", id="component"),
        pytest.param(ComponentLite, None, "name", "changed", id="component-lite"),
        pytest.param(
            Dependency,
            {"id": 1, "type": "COMPONENT", "group": "RESOURCE", "name": "X"},
            "name",
            "changed",
            id="dependency",
        ),
    ],
)
def test_model_is_frozen(model, data, field, new_value):
    if data is None:
        data = (
            _make_full_component_data()
            if model is Component
            else _make_component_lite_data()
        )
    instance = model.model_validate(data)
    with pytest.raises(ValidationError):
        setattr(instance, field, new_value)


def test_policy_model_ref_from_api_payload():
    ref = PolicyModelRef.model_validate(
        {"id": 42, "name": "Support Tickets", "shortName": "support_tickets"},
    )
    assert ref.id == 42
    assert ref.name == "Support Tickets"
    assert ref.short_name == "support_tickets"


def test_policy_model_ref_minimal():
    ref = PolicyModelRef.model_validate({"id": 42})
    assert ref.id == 42
    assert ref.name is None
    assert ref.short_name is None


def test_component_condition_from_api_payload():
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


def test_component_condition_minimal():
    cond = ComponentCondition.model_validate(
        {"attribute": "name", "operator": "!=", "value": "test"},
    )
    assert cond.rhs_type is None
    assert cond.rhsvalue is None


def test_component_condition_accepts_member_object_shape():
    cond = ComponentCondition.model_validate(
        {"operator": "IN", "member": {"id": 7, "name": "Eng"}, "notFound": False},
    )
    assert cond.operator == "IN"
    assert cond.attribute is None
    assert cond.value is None
    assert cond.member == {"id": 7, "name": "Eng"}
    assert cond.not_found is False


def test_component_accepts_member_object_member_conditions():
    data = _make_full_component_data()
    data["memberConditions"] = [
        {"operator": "IN", "member": {"id": 7, "name": "Eng"}, "notFound": False},
    ]
    comp = Component.model_validate(data)
    assert comp.member_conditions[0].member == {"id": 7, "name": "Eng"}
    assert comp.member_conditions[0].not_found is False


def test_component_accepts_string_actions():
    data = _make_full_component_data()
    data["actions"] = ["DELETE", "CONFIGURE"]
    comp = Component.model_validate(data)
    assert comp.actions == ["DELETE", "CONFIGURE"]


def test_authority_from_api_payload():
    auth = Authority.model_validate({"authority": "VIEW_COMPONENT"})
    assert auth.authority == "VIEW_COMPONENT"


def test_deployment_request_info_from_api_payload():
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


def test_component_from_api_payload():
    comp = Component.model_validate(_make_full_component_data())
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


def test_component_minimal():
    comp = Component.model_validate(
        {"id": 1, "name": "IT Department", "type": "SUBJECT", "status": "DRAFT"},
    )
    assert comp.id == 1
    assert comp.type == ComponentGroupType.SUBJECT
    assert comp.folder_id is None
    assert comp.description is None
    assert comp.tags == []
    assert comp.policy_model is None
    assert comp.conditions == []
    assert comp.deployment_request is None
    assert comp.version is None


def test_component_rejects_invalid_type():
    with pytest.raises(ValidationError):
        Component.model_validate(
            {"id": 1, "name": "X", "type": "INVALID", "status": "DRAFT"},
        )


def test_predicate_attribute_from_api_payload():
    pa = PredicateAttribute.model_validate(
        {"lhs": "category", "operator": "=", "rhs": "security"},
    )
    assert pa.lhs == "category"
    assert pa.operator == "="
    assert pa.rhs == "security"


def test_predicate_data_from_api_payload():
    raw = {
        "operator": None,
        "referenceIds": [1, 2],
        "attributes": [{"lhs": "x", "operator": "=", "rhs": "y"}],
        "actions": ["VIEW"],
    }
    pd = PredicateData.model_validate(raw)
    assert pd.operator is None
    assert pd.reference_ids == [1, 2]
    assert len(pd.attributes) == 1
    assert pd.actions == ["VIEW"]


def test_component_lite_from_api_payload():
    cl = ComponentLite.model_validate(_make_component_lite_data())
    assert cl.id == 101
    assert cl.name == "Security Vulnerabilities"
    assert cl.full_name == "RESOURCE/Security Vulnerabilities"
    assert cl.status == ComponentStatus.APPROVED
    assert cl.model_id == 42
    assert cl.model_type == "Support Tickets"
    assert cl.group == ComponentGroupType.RESOURCE
    assert cl.deployed is True
    assert cl.predicate_data is not None
    assert len(cl.predicate_data.attributes) == 1
    assert cl.predicate_data.attributes[0].lhs == "category"
    assert len(cl.tags) == 1
    assert cl.referred_in_policies is False
    assert cl.empty is False


def test_component_lite_accepts_openapi_minimal_payload():
    cl = ComponentLite.model_validate({"name": "Minimal", "status": "DRAFT"})
    assert cl.name == "Minimal"
    assert cl.status == ComponentStatus.DRAFT
    assert cl.id is None
    assert cl.model_id is None
    assert cl.model_type is None
    assert cl.group is None
    assert cl.last_updated_date is None
    assert cl.created_date is None
    assert cl.tags == []


def test_component_lite_rejects_missing_openapi_required():
    with pytest.raises(ValidationError):
        ComponentLite.model_validate({"name": "NoStatus"})
    with pytest.raises(ValidationError):
        ComponentLite.model_validate({"status": "DRAFT"})


def test_push_result_from_api_payload():
    pr = PushResult.model_validate(
        {
            "dpsUrl": "https://cc-prod-01:8443/dps",
            "success": True,
            "message": "Push Successful",
        },
    )
    assert pr.dps_url == "https://cc-prod-01:8443/dps"
    assert pr.success is True
    assert pr.message == "Push Successful"


def test_deployment_result_from_api_payload():
    raw = {
        "id": 101,
        "pushResults": [
            {
                "dpsUrl": "https://cc-prod-01:8443/dps",
                "success": True,
                "message": "Push Successful",
            },
        ],
    }
    dr = DeploymentResult.model_validate(raw)
    assert dr.id == 101
    assert len(dr.push_results) == 1
    assert dr.push_results[0].success is True


def test_deployment_result_empty_push_results():
    dr = DeploymentResult.model_validate({"id": 101})
    assert dr.push_results == []


def test_dependency_from_api_payload():
    raw = {
        "id": 50,
        "type": "COMPONENT",
        "group": "RESOURCE",
        "name": "Security Vulnerabilities",
        "folderPath": None,
        "optional": False,
        "provided": True,
        "sub": False,
    }
    dep = Dependency.model_validate(raw)
    assert dep.id == 50
    assert dep.type == "COMPONENT"
    assert dep.group == "RESOURCE"
    assert dep.name == "Security Vulnerabilities"
    assert dep.provided is True
    assert dep.sub is False


def test_dependency_with_null_group():
    dep = Dependency.model_validate(
        {"id": 60, "type": "POLICY", "group": None, "name": "Allow IT Access"},
    )
    assert dep.id == 60
    assert dep.type == "POLICY"
    assert dep.group is None
    assert dep.name == "Allow IT Access"


def test_dependency_without_group_field():
    dep = Dependency.model_validate(
        {"id": 61, "type": "POLICY", "name": "Deny External Access"}
    )
    assert dep.group is None


def test_component_name_data_from_api_payload():
    cnd = ComponentNameData.model_validate(
        {"policy_model_id": 42, "policy_model_name": "Support Tickets"},
    )
    assert cnd.policy_model_id == 42
    assert cnd.policy_model_name == "Support Tickets"


def test_component_name_entry_from_api_payload():
    raw = {
        "id": 101,
        "name": "Security Vulnerabilities",
        "empty": False,
        "status": "APPROVED",
        "data": {"policy_model_id": 42, "policy_model_name": "Support Tickets"},
    }
    cne = ComponentNameEntry.model_validate(raw)
    assert cne.id == 101
    assert cne.name == "Security Vulnerabilities"
    assert cne.empty is False
    assert cne.status == "APPROVED"
    assert cne.data is not None
    assert cne.data.policy_model_id == 42


def test_component_name_entry_without_data():
    cne = ComponentNameEntry.model_validate({"id": 1, "name": "X", "status": "DRAFT"})
    assert cne.data is None
    assert cne.empty is False


def test_component_accepts_null_owner_display_name():
    data = _make_full_component_data()
    data["ownerDisplayName"] = None
    comp = Component.model_validate(data)
    assert comp.owner_display_name is None


def test_component_accepts_null_modified_by():
    data = _make_full_component_data()
    data["modifiedBy"] = None
    comp = Component.model_validate(data)
    assert comp.modified_by is None


def test_component_lite_accepts_null_owner_and_modifier_metadata():
    data = _make_component_lite_data()
    data["ownerDisplayName"] = None
    data["modifiedBy"] = None
    lite = ComponentLite.model_validate(data)
    assert lite.owner_display_name is None
    assert lite.modified_by is None


def _entry_data() -> dict[str, object]:
    return {
        "id": 770,
        "revision": "3",
        "name": "ROOT_42/pentest_component",
        "description": None,
        "activeFrom": 1761133292235,
        "activeTo": 1761133292235,
        "componentDetail": None,
        "createdDate": 1761133292266,
        "createdBy": "me",
        "modifiedBy": "me",
        "lastUpdatedDate": 1761133292250,
        "submittedBy": "me",
        "submittedDate": 1761133292266,
        "actionType": "UN",
    }


def test_component_history_entry_parses_and_is_frozen():
    from nextlabs_sdk.cloudaz import ComponentHistoryEntry

    entry = ComponentHistoryEntry.model_validate(_entry_data())

    assert entry.id == 770
    assert entry.revision == 3  # API sends string "3"; coerced to int
    assert entry.active_from == 1761133292235
    assert entry.created_by == "me"
    assert entry.action_type == "UN"
    assert isinstance(entry.action_type, str)
    assert isinstance(entry.last_updated_date, int)
    # list view carries no embedded component
    assert "componentDetail" not in ComponentHistoryEntry.model_fields
    assert "component_detail" not in ComponentHistoryEntry.model_fields
    with pytest.raises(ValidationError):
        entry.name = "changed"  # type: ignore[misc]


def _make_revision_data() -> dict[str, object]:
    return {
        "id": 555,
        "revision": "1",
        "name": "ROOT_101/pentest_component",
        "description": None,
        "activeFrom": 1761133292235,
        "activeTo": 1761133292235,
        "componentDetail": _make_full_component_data(),
        "createdDate": 1761133292266,
        "createdBy": "me",
        "modifiedBy": "me",
        "lastUpdatedDate": 1761133292250,
        "submittedBy": "me",
        "submittedDate": 1761133292266,
        "actionType": None,
    }


def test_component_revision_from_api_payload():
    from nextlabs_sdk.cloudaz import ComponentRevision

    rev = ComponentRevision.model_validate(_make_revision_data())

    assert rev.id == 555
    assert rev.revision == 1  # API sends string "1"; coerced to int (AC5)
    assert rev.action_type is None
    assert isinstance(rev.component_detail, Component)
    assert rev.component_detail.id == _make_full_component_data()["id"]


def test_component_revision_mirrors_history_entry():
    from nextlabs_sdk.cloudaz import ComponentHistoryEntry, ComponentRevision

    assert set(ComponentHistoryEntry.model_fields) <= set(
        ComponentRevision.model_fields
    )
    assert "component_detail" in ComponentRevision.model_fields
    assert issubclass(ComponentRevision, ComponentHistoryEntry)
