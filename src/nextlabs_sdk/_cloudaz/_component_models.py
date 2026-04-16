from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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
