from __future__ import annotations

from nextlabs_sdk._pdp import _urns as urns
from nextlabs_sdk._pdp._enums import Decision
from nextlabs_sdk._pdp._request_models import (
    Action,
    Application,
    Environment,
    EvalRequest,
    PermissionsRequest,
    Resource,
    Subject,
)
from nextlabs_sdk._pdp._response_models import (
    ActionPermission,
    EvalResponse,
    EvalResult,
    Obligation,
    ObligationAttribute,
    PermissionsResponse,
    PolicyRef,
    Status,
)


def serialize_eval_request(request: EvalRequest) -> dict[str, object]:
    categories: list[dict[str, object]] = [
        _serialize_subject(request.subject),
        _serialize_action(request.action),
        _serialize_resource(request.resource),
        _serialize_application(request.application),
    ]
    if request.environment is not None:
        categories.append(_serialize_environment(request.environment))
    return {
        "Request": {
            "ReturnPolicyIdList": request.return_policy_ids,
            "Category": categories,
        },
    }


def serialize_permissions_request(
    request: PermissionsRequest,
) -> dict[str, object]:
    categories: list[dict[str, object]] = [
        _serialize_subject(request.subject),
        _serialize_resource(request.resource),
        _serialize_application(request.application),
    ]
    if request.environment is not None:
        categories.append(_serialize_environment(request.environment))
    response: dict[str, object] = {
        "Request": {
            "ReturnPolicyIdList": request.return_policy_ids,
            "Category": categories,
        },
    }
    if request.record_matching_policies:
        request_dict = response["Request"]
        if isinstance(request_dict, dict):
            request_dict["RecordMatchingPolicies"] = True
    return response


def deserialize_eval_response(body: dict[str, object]) -> EvalResponse:
    raw_results = body["Response"]
    result_list: list[EvalResult] = []
    if isinstance(raw_results, list):
        result_list = [_parse_eval_result(item) for item in raw_results]
    return EvalResponse(results=result_list)


def deserialize_permissions_response(
    body: dict[str, object],
) -> PermissionsResponse:
    allowed: list[ActionPermission] = []
    denied: list[ActionPermission] = []
    dont_care: list[ActionPermission] = []

    raw_results = body["Response"]
    if not isinstance(raw_results, list):
        return PermissionsResponse(
            allowed=allowed,
            denied=denied,
            dont_care=dont_care,
        )

    for raw_result in raw_results:
        if not isinstance(raw_result, dict):
            continue
        action_name = _extract_action_name(raw_result)
        obligations = _parse_obligations(raw_result.get("Obligations", []))
        policy_refs = _parse_policy_refs(raw_result)
        permission = ActionPermission(
            name=action_name,
            obligations=obligations,
            policy_refs=policy_refs,
        )
        decision = Decision(raw_result["Decision"])
        if decision == Decision.PERMIT:
            allowed.append(permission)
        elif decision == Decision.DENY:
            denied.append(permission)
        else:
            dont_care.append(permission)

    return PermissionsResponse(
        allowed=allowed,
        denied=denied,
        dont_care=dont_care,
    )


def _serialize_subject(subject: Subject) -> dict[str, object]:
    attrs: list[dict[str, object]] = [
        _make_attr(urns.SUBJECT_ID, subject.id),
    ]
    for key, attr_value in (subject.model_extra or {}).items():
        attrs.append(
            _make_attr(f"{urns.SUBJECT_PREFIX}{key}", attr_value),
        )
    for key, attr_value in subject.attributes.items():
        attrs.append(_make_attr(key, attr_value))
    return {
        "CategoryId": urns.SUBJECT_CATEGORY,
        "Attribute": attrs,
    }


def _serialize_resource(resource: Resource) -> dict[str, object]:
    attrs: list[dict[str, object]] = [
        _make_attr(urns.RESOURCE_ID, resource.id),
        _make_attr(urns.RESOURCE_TYPE, resource.type),
    ]
    if resource.dimension is not None:
        attrs.append(_make_attr(urns.RESOURCE_DIMENSION, resource.dimension.value))
    if resource.nocache:
        attrs.append(_make_attr(urns.RESOURCE_NOCACHE, True))
    for key, attr_value in (resource.model_extra or {}).items():
        attrs.append(
            _make_attr(f"{urns.RESOURCE_PREFIX}{key}", attr_value),
        )
    for key, attr_value in resource.attributes.items():
        attrs.append(_make_attr(key, attr_value))
    return {
        "CategoryId": urns.RESOURCE_CATEGORY,
        "Attribute": attrs,
    }


def _serialize_action(action: Action) -> dict[str, object]:
    return {
        "CategoryId": urns.ACTION_CATEGORY,
        "Attribute": [_make_attr(urns.ACTION_ID, action.id)],
    }


def _serialize_application(application: Application) -> dict[str, object]:
    attrs: list[dict[str, object]] = [
        _make_attr(urns.APPLICATION_ID, application.id),
    ]
    for key, attr_value in (application.model_extra or {}).items():
        attrs.append(
            _make_attr(f"{urns.APPLICATION_PREFIX}{key}", attr_value),
        )
    for key, attr_value in application.attributes.items():
        attrs.append(_make_attr(key, attr_value))
    return {
        "CategoryId": urns.APPLICATION_CATEGORY,
        "Attribute": attrs,
    }


def _serialize_environment(environment: Environment) -> dict[str, object]:
    attrs: list[dict[str, object]] = []
    for key, attr_value in (environment.model_extra or {}).items():
        attrs.append(
            _make_attr(f"{urns.ENVIRONMENT_PREFIX}{key}", attr_value),
        )
    for key, attr_value in environment.attributes.items():
        attrs.append(_make_attr(key, attr_value))
    return {
        "CategoryId": urns.ENVIRONMENT_CATEGORY,
        "Attribute": attrs,
    }


def _make_attr(
    attr_id: str,
    attr_value: str | int | float | bool,
) -> dict[str, object]:
    return {
        "AttributeId": attr_id,
        "Value": attr_value,
        "DataType": _infer_datatype(attr_value),
    }


def _infer_datatype(attr_value: str | int | float | bool) -> str:
    if isinstance(attr_value, bool):
        return urns.BOOLEAN_DATATYPE
    if isinstance(attr_value, int):
        return urns.INTEGER_DATATYPE
    if isinstance(attr_value, float):
        return urns.DOUBLE_DATATYPE
    return urns.STRING_DATATYPE


def _parse_eval_result(raw: dict[str, object]) -> EvalResult:
    decision = Decision(raw["Decision"])
    status_raw = raw["Status"]
    status = _parse_status(
        status_raw if isinstance(status_raw, dict) else {},
    )
    obligations_raw = raw.get("Obligations", [])
    obligations = _parse_obligations(
        obligations_raw if isinstance(obligations_raw, list) else [],
    )
    policy_refs = _parse_policy_refs(raw)
    return EvalResult(
        decision=decision,
        status=status,
        obligations=obligations,
        policy_refs=policy_refs,
    )


def _parse_status(raw: dict[str, object]) -> Status:
    status_code_raw = raw["StatusCode"]
    code_value = ""
    if isinstance(status_code_raw, dict):
        code_value = str(status_code_raw.get("Value", ""))
    message_raw = raw.get("StatusMessage", "")
    message = str(message_raw) if message_raw else ""
    return Status(code=code_value, message=message)


def _parse_obligations(
    raw_obligations: list[object],
) -> list[Obligation]:
    obligations: list[Obligation] = []
    for raw in raw_obligations:
        if not isinstance(raw, dict):
            continue
        attrs = [
            ObligationAttribute(id=str(a["AttributeId"]), value=str(a["Value"]))
            for a in raw.get("AttributeAssignment", [])
            if isinstance(a, dict)
        ]
        obligations.append(Obligation(id=str(raw["Id"]), attributes=attrs))
    return obligations


def _parse_policy_refs(raw: dict[str, object]) -> list[PolicyRef]:
    policy_id_list = raw.get("PolicyIdentifierList", {})
    if not isinstance(policy_id_list, dict):
        return []
    raw_refs = policy_id_list.get("PolicyIdReference", [])
    if not isinstance(raw_refs, list):
        return []
    result: list[PolicyRef] = []
    for ref_item in raw_refs:
        if not isinstance(ref_item, dict):
            continue
        result.append(
            PolicyRef(
                id=str(ref_item["Id"]),
                version=str(ref_item.get("Version", "")),
            ),
        )
    return result


def _extract_action_name(raw_result: dict[str, object]) -> str:
    categories = raw_result.get("Category", [])
    if not isinstance(categories, list):
        return ""
    for category in categories:
        if not isinstance(category, dict):
            continue
        if category["CategoryId"] == urns.ACTION_CATEGORY:
            attributes = category.get("Attribute", [])
            if not isinstance(attributes, list):
                continue
            for attr in attributes:
                if not isinstance(attr, dict):
                    continue
                if attr["AttributeId"] == urns.ACTION_ID:
                    return str(attr["Value"])
    return ""
