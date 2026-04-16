from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from nextlabs_sdk._pdp._enums import Decision


class Status(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    message: str = ""


class ObligationAttribute(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    attr_value: str


class Obligation(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    attributes: list[ObligationAttribute] = []


class PolicyRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: str = ""


class EvalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: Decision
    status: Status
    obligations: list[Obligation] = []
    policy_refs: list[PolicyRef] = []


class EvalResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    eval_results: list[EvalResult]

    @property
    def first_result(self) -> EvalResult:
        return self.eval_results[0]


class ActionPermission(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    obligations: list[Obligation] = []
    policy_refs: list[PolicyRef] = []


class PermissionsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    allowed: list[ActionPermission] = []
    denied: list[ActionPermission] = []
    dont_care: list[ActionPermission] = []
