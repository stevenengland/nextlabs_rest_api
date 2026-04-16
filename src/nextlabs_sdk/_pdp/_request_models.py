from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from nextlabs_sdk._pdp._enums import ResourceDimension


class Subject(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    id: str
    attributes: dict[str, str | int | float | bool] = {}

    @classmethod
    def simple(cls, subject_id: str) -> Subject:
        return cls(id=subject_id)


class Resource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    id: str
    type: str
    dimension: ResourceDimension | None = None
    nocache: bool = False
    attributes: dict[str, str | int | float | bool] = {}

    @classmethod
    def simple(cls, resource_id: str, resource_type: str) -> Resource:
        return cls(id=resource_id, type=resource_type)


class Action(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str


class Application(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    id: str
    attributes: dict[str, str | int | float | bool] = {}


class Environment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    attributes: dict[str, str | int | float | bool] = {}


class EvalRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: Subject
    resource: Resource
    action: Action
    application: Application
    environment: Environment | None = None
    return_policy_ids: bool = False


class PermissionsRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: Subject
    resource: Resource
    application: Application
    environment: Environment | None = None
    return_policy_ids: bool = False
    record_matching_policies: bool = False
