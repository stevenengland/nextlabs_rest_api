from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from nextlabs_sdk._cloudaz._models import Tag


class ComponentGroupType(str, Enum):
    SUBJECT = "SUBJECT"
    RESOURCE = "RESOURCE"
    ACTION = "ACTION"


class ComponentStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    OBSOLETE = "OBSOLETE"


class PolicyModelRef(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int  # noqa: WPS125
    name: str | None = None
    short_name: str | None = Field(default=None, alias="shortName")


class ComponentCondition(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    attribute: str
    operator: str
    value: str  # noqa: WPS110
    rhs_type: str | None = Field(default=None, alias="rhsType")
    rhsvalue: str | None = None


class Authority(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    authority: str


class DeploymentRequestInfo(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int  # noqa: WPS125
    type: str  # noqa: WPS125
    push: bool
    deployment_time: int = Field(alias="deploymentTime")
    deploy_dependencies: bool = Field(alias="deployDependencies")


class Component(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int  # noqa: WPS125
    folder_id: int | None = Field(default=None, alias="folderId")
    name: str
    description: str | None = None
    tags: list[Tag] = Field(default_factory=list)
    type: ComponentGroupType  # noqa: WPS125
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
    status: ComponentStatus
    parent_id: int | None = Field(default=None, alias="parentId")
    parent_name: str | None = Field(default=None, alias="parentName")
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
