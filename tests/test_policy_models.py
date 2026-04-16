from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from nextlabs_sdk._cloudaz._models import TagType
from nextlabs_sdk._cloudaz._policy_models import (
    ComponentGroup,
    EnvironmentConfig,
    ExportOptions,
    ImportResult,
    Policy,
    PolicyComponentRef,
    PolicyLite,
    PolicyObligation,
)


def test_policy_component_ref_minimal() -> None:
    raw: dict[str, Any] = {"id": 42}
    ref = PolicyComponentRef.model_validate(raw)
    assert ref.id == 42
    assert ref.name is None
    assert ref.type is None
    assert ref.status is None
    assert ref.tags == []
    assert ref.conditions == []
    assert ref.policy_model is None
    assert ref.deployment_request is None
    assert ref.version is None


def test_policy_component_ref_full() -> None:
    raw: dict[str, Any] = {
        "id": 101,
        "folderId": 5,
        "name": "Security Vulnerabilities",
        "description": "A component ref",
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
        "policyModel": {"id": 42, "name": "Support Tickets"},
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
        "folderPath": "/policies/helpdesk",
        "preCreated": False,
        "version": 1,
        "hasInactiveSubComponets": False,
        "deploymentPending": False,
    }
    ref = PolicyComponentRef.model_validate(raw)
    assert ref.id == 101
    assert ref.name == "Security Vulnerabilities"
    assert ref.type == "RESOURCE"
    assert ref.status == "DRAFT"
    assert len(ref.tags) == 1
    assert ref.tags[0].type == TagType.COMPONENT
    assert len(ref.conditions) == 1
    assert ref.conditions[0].attribute == "category"
    assert ref.policy_model is not None
    assert ref.policy_model.id == 42
    assert ref.deployment_request is not None
    assert ref.deployment_request.deploy_dependencies is True
    assert ref.has_inactive_sub_components is False


def test_policy_component_ref_is_frozen() -> None:
    ref = PolicyComponentRef.model_validate({"id": 42})
    with pytest.raises(ValidationError):
        ref.id = 99  # type: ignore[misc]


def test_component_group_from_api_payload() -> None:
    raw: dict[str, Any] = {
        "operator": "IN",
        "components": [{"id": 42}, {"id": 43}],
    }
    group = ComponentGroup.model_validate(raw)
    assert group.operator == "IN"
    assert len(group.components) == 2
    assert group.components[0].id == 42
    assert group.components[1].id == 43


def test_component_group_empty_components() -> None:
    raw: dict[str, Any] = {"operator": "IN"}
    group = ComponentGroup.model_validate(raw)
    assert group.components == []


def test_component_group_is_frozen() -> None:
    group = ComponentGroup.model_validate({"operator": "IN"})
    with pytest.raises(ValidationError):
        group.operator = "NOT_IN"  # type: ignore[misc]


def test_policy_obligation_from_api_payload() -> None:
    raw: dict[str, Any] = {
        "id": 10,
        "policyModelId": 42,
        "name": "log_obligation",
        "params": {"level": "INFO", "message": "Access granted"},
    }
    obl = PolicyObligation.model_validate(raw)
    assert obl.id == 10
    assert obl.policy_model_id == 42
    assert obl.name == "log_obligation"
    assert obl.params == {"level": "INFO", "message": "Access granted"}


def test_policy_obligation_minimal() -> None:
    raw: dict[str, Any] = {"name": "notify"}
    obl = PolicyObligation.model_validate(raw)
    assert obl.id is None
    assert obl.policy_model_id == 0
    assert obl.name == "notify"
    assert obl.params == {}


def test_policy_obligation_is_frozen() -> None:
    obl = PolicyObligation.model_validate({"name": "log"})
    with pytest.raises(ValidationError):
        obl.name = "changed"  # type: ignore[misc]


def test_environment_config_from_api_payload() -> None:
    raw: dict[str, Any] = {"remoteAccess": 1, "timeSinceLastHBSecs": 300}
    env = EnvironmentConfig.model_validate(raw)
    assert env.remote_access == 1
    assert env.time_since_last_hb_secs == 300


def test_environment_config_defaults() -> None:
    raw: dict[str, Any] = {}
    env = EnvironmentConfig.model_validate(raw)
    assert env.remote_access == -1
    assert env.time_since_last_hb_secs == -1


def test_environment_config_is_frozen() -> None:
    env = EnvironmentConfig.model_validate({})
    with pytest.raises(ValidationError):
        env.remote_access = 5  # type: ignore[misc]


def test_export_options_from_api_payload() -> None:
    raw: dict[str, Any] = {"sandeEnabled": True, "plainTextEnabled": False}
    opts = ExportOptions.model_validate(raw)
    assert opts.sande_enabled is True
    assert opts.plain_text_enabled is False


def test_export_options_is_frozen() -> None:
    opts = ExportOptions.model_validate(
        {"sandeEnabled": False, "plainTextEnabled": True},
    )
    with pytest.raises(ValidationError):
        opts.sande_enabled = True  # type: ignore[misc]


def test_import_result_from_api_payload() -> None:
    raw: dict[str, Any] = {
        "total_components": 5,
        "total_policies": 3,
        "total_policy_models": 2,
        "non_blocking_error": False,
    }
    ir = ImportResult.model_validate(raw)
    assert ir.total_components == 5
    assert ir.total_policies == 3
    assert ir.total_policy_models == 2
    assert ir.non_blocking_error is False


def test_import_result_is_frozen() -> None:
    ir = ImportResult.model_validate(
        {
            "total_components": 1,
            "total_policies": 1,
            "total_policy_models": 1,
            "non_blocking_error": False,
        },
    )
    with pytest.raises(ValidationError):
        ir.total_policies = 99  # type: ignore[misc]


def _make_full_policy_data() -> dict[str, Any]:
    return {
        "id": 82,
        "folderId": 3,
        "name": "Allow IT Ticket Access",
        "fullName": "Allow IT Ticket Access",
        "description": "Allows IT department to access support tickets",
        "status": "DRAFT",
        "category": "Policy",
        "effectType": "allow",
        "tags": [
            {
                "id": 30,
                "key": "helpdesk_policy",
                "label": "Helpdesk_Policy",
                "type": "POLICY_TAG",
                "status": "ACTIVE",
            },
        ],
        "parentId": None,
        "parentName": None,
        "hasParent": False,
        "hasSubPolicies": False,
        "subjectComponents": [
            {
                "operator": "IN",
                "components": [{"id": 50}],
            },
        ],
        "hasToSubjectComponents": False,
        "toSubjectComponents": [],
        "actionComponents": [
            {
                "operator": "IN",
                "components": [{"id": 60}],
            },
        ],
        "fromResourceComponents": [
            {
                "operator": "IN",
                "components": [{"id": 101}],
            },
        ],
        "hasToResourceComponents": False,
        "toResourceComponents": [],
        "environmentConfig": {
            "remoteAccess": -1,
            "timeSinceLastHBSecs": -1,
        },
        "scheduleConfig": None,
        "expression": "",
        "allowObligations": [
            {
                "id": 10,
                "policyModelId": 42,
                "name": "log_obligation",
                "params": {"level": "INFO", "message": "Access granted"},
            },
        ],
        "denyObligations": [],
        "subPolicy": False,
        "subPolicyRefs": [],
        "attributes": [],
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
        "reIndexNow": True,
        "skipAddingTrueAllowAttribute": False,
        "version": 1,
        "authorities": [{"authority": "VIEW_POLICY"}],
        "manualDeploy": False,
        "deploymentTargets": [],
        "deploymentRequest": None,
        "folderPath": "/policies/helpdesk",
        "activeWorkflowRequest": None,
        "componentIds": [50, 60, 101],
        "hidden": False,
        "deploymentPending": False,
        "type": None,
    }


def test_policy_from_api_payload() -> None:
    raw = _make_full_policy_data()
    policy = Policy.model_validate(raw)
    assert policy.id == 82
    assert policy.name == "Allow IT Ticket Access"
    assert policy.full_name == "Allow IT Ticket Access"
    assert policy.description == "Allows IT department to access support tickets"
    assert policy.status == "DRAFT"
    assert policy.effect_type == "allow"
    assert len(policy.tags) == 1
    assert policy.tags[0].type == TagType.POLICY
    assert policy.has_parent is False
    assert policy.has_sub_policies is False
    assert len(policy.subject_components) == 1
    assert policy.subject_components[0].operator == "IN"
    assert len(policy.subject_components[0].components) == 1
    assert policy.subject_components[0].components[0].id == 50
    assert len(policy.action_components) == 1
    assert len(policy.from_resource_components) == 1
    assert policy.to_resource_components == []
    assert policy.environment_config is not None
    assert policy.environment_config.remote_access == -1
    assert len(policy.allow_obligations) == 1
    assert policy.allow_obligations[0].name == "log_obligation"
    assert policy.allow_obligations[0].params["level"] == "INFO"
    assert policy.deny_obligations == []
    assert policy.sub_policy is False
    assert policy.version == 1
    assert policy.manual_deploy is False
    assert policy.component_ids == [50, 60, 101]
    assert policy.deployment_pending is False
    assert policy.type is None


def test_policy_minimal() -> None:
    raw: dict[str, Any] = {
        "id": 1,
        "name": "Minimal Policy",
        "status": "DRAFT",
        "effectType": "deny",
    }
    policy = Policy.model_validate(raw)
    assert policy.id == 1
    assert policy.effect_type == "deny"
    assert policy.folder_id is None
    assert policy.full_name is None
    assert policy.description is None
    assert policy.tags == []
    assert policy.subject_components == []
    assert policy.action_components == []
    assert policy.from_resource_components == []
    assert policy.environment_config is None
    assert policy.allow_obligations == []
    assert policy.deny_obligations == []
    assert policy.version is None
    assert policy.deployment_request is None
    assert policy.component_ids is None


def test_policy_is_frozen() -> None:
    policy = Policy.model_validate(_make_full_policy_data())
    with pytest.raises(ValidationError):
        policy.name = "changed"  # type: ignore[misc]


def _make_policy_lite_data() -> dict[str, Any]:
    return {
        "id": 82,
        "folderId": 3,
        "folderName": "helpdesk",
        "folderPath": "/policies/helpdesk",
        "name": "Allow IT Ticket Access",
        "lowercase_name": "allow it ticket access",
        "rootFolder": None,
        "policyFullName": "Allow IT Ticket Access",
        "description": "Allows IT department to access support tickets",
        "status": "APPROVED",
        "effectType": "allow",
        "lastUpdatedDate": 1713173211329,
        "createdDate": 1713171640267,
        "hasParent": False,
        "hasSubPolicies": False,
        "ownerId": 0,
        "ownerDisplayName": "Administrator",
        "modifiedById": 0,
        "modifiedBy": "Administrator",
        "tags": [
            {
                "id": 30,
                "key": "helpdesk_policy",
                "label": "Helpdesk_Policy",
                "type": "POLICY_TAG",
                "status": "ACTIVE",
            },
        ],
        "noOfTags": 1,
        "parentPolicy": None,
        "subPolicies": [],
        "childNodes": [],
        "authorities": [{"authority": "VIEW_POLICY"}],
        "manualDeploy": False,
        "deploymentTime": 1713173211332,
        "deployed": True,
        "actionType": "DE",
        "activeWorkflowId": None,
        "activeEntityWorkflowRequestStatus": None,
        "activeWorkflowRequestLevelStatus": None,
        "revisionCount": 1,
        "version": 2,
        "componentIds": [50, 60, 101],
        "obligationModelIds": [42],
        "hideMoreDetails": False,
        "deploymentPending": False,
    }


def test_policy_lite_from_api_payload() -> None:
    raw = _make_policy_lite_data()
    pl = PolicyLite.model_validate(raw)
    assert pl.id == 82
    assert pl.name == "Allow IT Ticket Access"
    assert pl.policy_full_name == "Allow IT Ticket Access"
    assert pl.status == "APPROVED"
    assert pl.effect_type == "allow"
    assert pl.has_parent is False
    assert pl.has_sub_policies is False
    assert len(pl.tags) == 1
    assert pl.tags[0].type == TagType.POLICY
    assert pl.no_of_tags == 1
    assert pl.parent_policy is None
    assert pl.sub_policies == []
    assert pl.deployed is True
    assert pl.component_ids == [50, 60, 101]
    assert pl.obligation_model_ids == [42]
    assert pl.hide_more_details is False
    assert pl.deployment_pending is False


def test_policy_lite_minimal() -> None:
    raw: dict[str, Any] = {
        "id": 1,
        "name": "Minimal",
        "status": "DRAFT",
        "effectType": "deny",
        "lastUpdatedDate": 1713171640267,
        "createdDate": 1713171640267,
    }
    pl = PolicyLite.model_validate(raw)
    assert pl.id == 1
    assert pl.effect_type == "deny"
    assert pl.folder_name is None
    assert pl.folder_path is None
    assert pl.root_folder is None
    assert pl.tags == []
    assert pl.parent_policy is None
    assert pl.component_ids is None
    assert pl.obligation_model_ids is None


def test_policy_lite_is_frozen() -> None:
    pl = PolicyLite.model_validate(_make_policy_lite_data())
    with pytest.raises(ValidationError):
        pl.name = "changed"  # type: ignore[misc]
