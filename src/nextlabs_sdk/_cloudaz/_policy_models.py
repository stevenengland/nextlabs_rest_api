from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from nextlabs_sdk._cloudaz._component_models import (
    Authority,
    ComponentCondition,
    DeploymentRequestInfo,
    PolicyModelRef,
)
from nextlabs_sdk._cloudaz._models import Tag


class PolicyComponentRef(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int  # noqa: WPS125
    folder_id: int | None = Field(default=None, alias="folderId")
    name: str | None = None
    description: str | None = None
    tags: list[Tag] = Field(default_factory=list)
    type: str | None = None  # noqa: WPS125
    category: str | None = None
    policy_model: PolicyModelRef | None = Field(
        default=None,
        alias="policyModel",
    )
    actions: list[dict[str, Any]] = Field(default_factory=list)
    conditions: list[ComponentCondition] = Field(default_factory=list)
    member_conditions: list[ComponentCondition] = Field(
        default_factory=list,
        alias="memberConditions",
    )
    sub_components: list[dict[str, Any]] = Field(
        default_factory=list,
        alias="subComponents",
    )
    status: str | None = None
    parent_id: int | None = Field(default=None, alias="parentId")
    parent_name: str | None = Field(default=None, alias="parentName")
    deployment_time: int = Field(default=0, alias="deploymentTime")
    deployed: bool = False
    action_type: str | None = Field(default=None, alias="actionType")
    revision_count: int = Field(default=0, alias="revisionCount")
    owner_id: int = Field(default=0, alias="ownerId")
    owner_display_name: str | None = Field(
        default=None,
        alias="ownerDisplayName",
    )
    created_date: int = Field(default=0, alias="createdDate")
    modified_by_id: int = Field(default=0, alias="modifiedById")
    modified_by: str | None = Field(default=None, alias="modifiedBy")
    last_updated_date: int = Field(default=0, alias="lastUpdatedDate")
    skip_validate: bool = Field(default=False, alias="skipValidate")
    re_index_all_now: bool = Field(default=True, alias="reIndexAllNow")
    hidden: bool = False
    authorities: list[Authority] = Field(default_factory=list)
    deployment_request: DeploymentRequestInfo | None = Field(
        default=None,
        alias="deploymentRequest",
    )
    folder_path: str | None = Field(default=None, alias="folderPath")
    pre_created: bool = Field(default=False, alias="preCreated")
    version: int | None = None
    has_inactive_sub_components: bool = Field(
        default=False,
        alias="hasInactiveSubComponets",
    )
    deployment_pending: bool = Field(default=False, alias="deploymentPending")


class ComponentGroup(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    operator: str
    components: list[PolicyComponentRef] = Field(default_factory=list)


class PolicyObligation(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int | None = None  # noqa: WPS125
    policy_model_id: int = Field(default=0, alias="policyModelId")
    name: str
    params: dict[str, str] = Field(default_factory=dict)  # noqa: WPS110


class EnvironmentConfig(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    remote_access: int = Field(default=-1, alias="remoteAccess")
    time_since_last_hb_secs: int = Field(
        default=-1,
        alias="timeSinceLastHBSecs",
    )


class ExportOptions(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    sande_enabled: bool = Field(alias="sandeEnabled")
    plain_text_enabled: bool = Field(alias="plainTextEnabled")


class ImportResult(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    total_components: int
    total_policies: int
    total_policy_models: int
    non_blocking_error: bool


class Policy(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int  # noqa: WPS125
    folder_id: int | None = Field(default=None, alias="folderId")
    name: str
    full_name: str | None = Field(default=None, alias="fullName")
    description: str | None = None
    status: str
    category: str | None = None
    effect_type: str = Field(alias="effectType")
    tags: list[Tag] = Field(default_factory=list)
    parent_id: int | None = Field(default=None, alias="parentId")
    parent_name: str | None = Field(default=None, alias="parentName")
    has_parent: bool = Field(default=False, alias="hasParent")
    has_sub_policies: bool = Field(default=False, alias="hasSubPolicies")
    subject_components: list[ComponentGroup] = Field(
        default_factory=list,
        alias="subjectComponents",
    )
    has_to_subject_components: bool = Field(
        default=False,
        alias="hasToSubjectComponents",
    )
    to_subject_components: list[ComponentGroup] = Field(
        default_factory=list,
        alias="toSubjectComponents",
    )
    action_components: list[ComponentGroup] = Field(
        default_factory=list,
        alias="actionComponents",
    )
    from_resource_components: list[ComponentGroup] = Field(
        default_factory=list,
        alias="fromResourceComponents",
    )
    has_to_resource_components: bool = Field(
        default=False,
        alias="hasToResourceComponents",
    )
    to_resource_components: list[ComponentGroup] = Field(
        default_factory=list,
        alias="toResourceComponents",
    )
    environment_config: EnvironmentConfig | None = Field(
        default=None,
        alias="environmentConfig",
    )
    schedule_config: dict[str, Any] | None = Field(
        default=None,
        alias="scheduleConfig",
    )
    expression: str = ""
    allow_obligations: list[PolicyObligation] = Field(
        default_factory=list,
        alias="allowObligations",
    )
    deny_obligations: list[PolicyObligation] = Field(
        default_factory=list,
        alias="denyObligations",
    )
    sub_policy: bool = Field(default=False, alias="subPolicy")
    sub_policy_refs: list[dict[str, Any]] = Field(
        default_factory=list,
        alias="subPolicyRefs",
    )
    attributes: list[str] = Field(default_factory=list)
    deployment_time: int = Field(default=0, alias="deploymentTime")
    deployed: bool = False
    action_type: str | None = Field(default=None, alias="actionType")
    revision_count: int = Field(default=0, alias="revisionCount")
    owner_id: int = Field(default=0, alias="ownerId")
    owner_display_name: str = Field(default="", alias="ownerDisplayName")
    created_date: int = Field(default=0, alias="createdDate")
    modified_by_id: int = Field(default=0, alias="modifiedById")
    modified_by: str = Field(default="", alias="modifiedBy")
    last_updated_date: int = Field(default=0, alias="lastUpdatedDate")
    skip_validate: bool = Field(default=False, alias="skipValidate")
    re_index_now: bool = Field(default=True, alias="reIndexNow")
    skip_adding_true_allow_attribute: bool = Field(
        default=False,
        alias="skipAddingTrueAllowAttribute",
    )
    version: int | None = None
    authorities: list[Authority] = Field(default_factory=list)
    manual_deploy: bool = Field(default=False, alias="manualDeploy")
    deployment_targets: list[dict[str, Any]] = Field(
        default_factory=list,
        alias="deploymentTargets",
    )
    deployment_request: DeploymentRequestInfo | None = Field(
        default=None,
        alias="deploymentRequest",
    )
    folder_path: str | None = Field(default=None, alias="folderPath")
    active_workflow_request: dict[str, Any] | None = Field(
        default=None,
        alias="activeWorkflowRequest",
    )
    component_ids: list[int] | None = Field(
        default=None,
        alias="componentIds",
    )
    hidden: bool = False
    deployment_pending: bool = Field(default=False, alias="deploymentPending")
    type: str | None = None  # noqa: WPS125


class PolicyLite(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int  # noqa: WPS125
    folder_id: int = Field(default=-1, alias="folderId")
    folder_name: str | None = Field(default=None, alias="folderName")
    folder_path: str | None = Field(default=None, alias="folderPath")
    name: str
    lowercase_name: str = Field(default="", alias="lowercase_name")
    root_folder: str | None = Field(default=None, alias="rootFolder")
    policy_full_name: str = Field(default="", alias="policyFullName")
    description: str | None = None
    status: str
    effect_type: str = Field(alias="effectType")
    last_updated_date: int = Field(alias="lastUpdatedDate")
    created_date: int = Field(alias="createdDate")
    has_parent: bool = Field(default=False, alias="hasParent")
    has_sub_policies: bool = Field(default=False, alias="hasSubPolicies")
    owner_id: int = Field(default=0, alias="ownerId")
    owner_display_name: str = Field(default="", alias="ownerDisplayName")
    modified_by_id: int = Field(default=0, alias="modifiedById")
    modified_by: str = Field(default="", alias="modifiedBy")
    tags: list[Tag] = Field(default_factory=list)
    no_of_tags: int = Field(default=0, alias="noOfTags")
    parent_policy: dict[str, Any] | None = Field(
        default=None,
        alias="parentPolicy",
    )
    sub_policies: list[dict[str, Any]] = Field(
        default_factory=list,
        alias="subPolicies",
    )
    child_nodes: list[dict[str, Any]] = Field(
        default_factory=list,
        alias="childNodes",
    )
    authorities: list[Authority] = Field(default_factory=list)
    manual_deploy: bool = Field(default=False, alias="manualDeploy")
    deployment_time: int = Field(default=0, alias="deploymentTime")
    deployed: bool = False
    action_type: str | None = Field(default=None, alias="actionType")
    active_workflow_id: int | None = Field(
        default=None,
        alias="activeWorkflowId",
    )
    active_entity_workflow_request_status: str | None = Field(
        default=None,
        alias="activeEntityWorkflowRequestStatus",
    )
    active_workflow_request_level_status: str | None = Field(
        default=None,
        alias="activeWorkflowRequestLevelStatus",
    )
    revision_count: int = Field(default=0, alias="revisionCount")
    version: int | None = None
    component_ids: list[int] | None = Field(
        default=None,
        alias="componentIds",
    )
    obligation_model_ids: list[int] | None = Field(
        default=None,
        alias="obligationModelIds",
    )
    hide_more_details: bool = Field(default=False, alias="hideMoreDetails")
    deployment_pending: bool = Field(default=False, alias="deploymentPending")
