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
from nextlabs_sdk.cloudaz import (
    Component,
    ComponentLite,
    ComponentRevision,
    MemberCondition,
    MemberDTO,
    TagType,
)
from tests.cloudaz.membership_helpers import (
    composite_component_data,
    dump_member_condition,
)


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
            MemberCondition,
            {"operator": "IN"},
            "operator",
            "NOT",
            id="member-condition",
        ),
        pytest.param(MemberDTO, {"id": 87}, "id", 88, id="member-dto"),
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


def test_component_preserves_all_member_fields():
    members = [
        {
            "id": 87,
            "name": "Team",
            "type": "MEMBER",
            "status": "APPROVED",
            "notFound": False,
            "description": "First member",
            "memberType": "USER_GROUP",
            "uid": "u87",
            "uniqueName": "team-87",
            "domainName": "example",
        },
        {
            "id": 88,
            "name": "User",
            "type": "SUBJECT",
            "status": "DELETED",
            "notFound": True,
            "description": "Second member",
            "memberType": "USER",
            "uid": "u88",
            "uniqueName": "user-88",
            "domainName": "example",
        },
    ]
    result = Component.model_validate(
        composite_component_data("IN", members),
    )

    actual = dump_member_condition(result)
    assert actual["members"] == members
    assert actual["operator"] == "IN"
    assert set(actual) == {"operator", "members"}


@pytest.mark.parametrize("operator", ["IN", "NOT"])
def test_component_revision_preserves_plural_members(operator):
    members = [
        {"id": 87, "name": "Member", "notFound": False},
        {"id": 88, "name": "Other", "notFound": True},
    ]
    result = ComponentRevision.model_validate(
        {
            "id": 555,
            "revision": "1",
            "componentDetail": composite_component_data(operator, members),
        },
    )

    actual = dump_member_condition(result)
    assert actual["operator"] == operator
    assert [member["id"] for member in actual["members"]] == [87, 88]
    assert [member["notFound"] for member in actual["members"]] == [False, True]


@pytest.mark.parametrize(
    "condition",
    [
        {"operator": "="},
        {"attribute": None, "operator": "=", "value": None},
        {
            "attribute": "name",
            "operator": "=",
            "value": "finance",
            "rhsType": "CONSTANT",
            "rhsvalue": "finance",
        },
    ],
)
def test_component_predicates_have_no_membership_fields(condition):
    result = Component.model_validate(
        {
            "id": 101,
            "name": "Ordinary",
            "type": "SUBJECT",
            "status": "DRAFT",
            "conditions": [condition],
        },
    )

    actual = result.model_dump(by_alias=True, mode="json")["conditions"][0]
    assert actual["attribute"] == condition.get("attribute")
    assert actual["operator"] == condition["operator"]
    assert actual["value"] == condition.get("value")
    assert actual["rhsType"] == condition.get("rhsType")
    assert actual["rhsvalue"] == condition.get("rhsvalue")
    assert "member" not in actual
    assert "notFound" not in actual
    assert not hasattr(result.conditions[0], "member")
    assert not hasattr(result.conditions[0], "not_found")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"operator": "IN", "members": []},
        {
            "operator": None,
            "members": [
                {
                    "id": None,
                    "name": None,
                    "type": None,
                    "status": None,
                    "notFound": None,
                    "description": None,
                    "memberType": None,
                    "uid": None,
                    "uniqueName": None,
                    "domainName": None,
                },
            ],
        },
        {
            "operator": "NOT",
            "members": [
                {
                    "id": 87,
                    "name": "Member",
                    "type": "MEMBER",
                    "status": "DRAFT",
                    "notFound": False,
                    "description": "Public DTO",
                    "memberType": "USER",
                    "uid": "u87",
                    "uniqueName": "member-87",
                    "domainName": "example",
                },
                {},
            ],
        },
    ],
    ids=["omitted", "empty", "optional-null", "filled"],
)
def test_public_membership_dtos_handle_optional_fields(payload):
    result = MemberCondition.model_validate(payload)

    serialized = result.model_dump(by_alias=True, mode="json")
    assert serialized["operator"] == payload.get("operator")
    assert len(serialized["members"]) == len(payload.get("members", []))
    assert all(isinstance(member, MemberDTO) for member in result.members)
    for supplied, actual in zip(payload.get("members", []), serialized["members"]):
        assert all(
            actual[key] == supplied_value for key, supplied_value in supplied.items()
        )


def test_public_membership_dtos_preserve_out_of_spec_values():
    member_values = {
        "id": 87,
        "type": "FUTURE_TYPE",
        "status": "OBSOLETE",
        "memberType": "CONTACT",
        "notFound": False,
    }
    payload = {
        "operator": "FUTURE_OPERATOR",
        "members": [member_values],
    }
    result = MemberCondition.model_validate(payload)

    actual = result.model_dump(by_alias=True, mode="json")
    assert actual["operator"] == "FUTURE_OPERATOR"
    assert all(
        actual["members"][0][key] == supplied_value
        for key, supplied_value in member_values.items()
    )


def test_public_membership_dtos_accept_python_field_names():
    member = MemberDTO(
        id=87,
        not_found=False,
        member_type="USER",
        unique_name="member-87",
        domain_name="example",
    )
    condition = MemberCondition(operator="IN", members=[member])

    actual = condition.model_dump(by_alias=True, mode="json")["members"][0]
    assert actual["notFound"] is False
    assert actual["memberType"] == "USER"
    assert actual["uniqueName"] == "member-87"
    assert actual["domainName"] == "example"
    assert "not_found" not in actual
    assert "member_type" not in actual
    assert "unique_name" not in actual
    assert "domain_name" not in actual


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
