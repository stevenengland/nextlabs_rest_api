from __future__ import annotations

import httpx

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
from nextlabs_sdk._pdp._status_check import raise_if_not_ok

_CATEGORY_ID_KEY = "CategoryId"
_ATTRIBUTE_KEY = "Attribute"
_VALUE_KEY = "Value"

AttrValue = str | int | float | bool
AttrPair = tuple[str, AttrValue]


def _collect_extra_attrs(
    model_extra: dict[str, object] | None,
    prefix: str,
) -> list[AttrPair]:
    collected: list[AttrPair] = []
    for key, extra_val in (model_extra or {}).items():
        collected.append((f"{prefix}{key}", _coerce_attr(extra_val)))
    return collected


def _coerce_attr(raw: object) -> AttrValue:
    if isinstance(raw, (str, int, float, bool)):
        return raw
    return str(raw)


def _collect_dict_attrs(
    attributes: dict[str, str | int | float | bool],
) -> list[AttrPair]:
    return list(attributes.items())


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
    environment_category = _serialize_permissions_environment(
        request.environment,
        record_matching_policies=request.record_matching_policies,
    )
    if environment_category is not None:
        categories.append(environment_category)
    return {
        "Request": {
            "ReturnPolicyIdList": request.return_policy_ids,
            "Category": categories,
        },
    }


def _serialize_permissions_environment(
    environment: Environment | None,
    *,
    record_matching_policies: bool,
) -> dict[str, object] | None:
    if environment is None and not record_matching_policies:
        return None
    if environment is None:
        category = _build_category(urns.ENVIRONMENT_CATEGORY, [])
    else:
        category = _serialize_environment(environment)
    if record_matching_policies:
        attributes = category[_ATTRIBUTE_KEY]
        assert isinstance(attributes, list)
        attributes.append(_make_record_matching_attr())
    return category


def _make_record_matching_attr() -> dict[str, object]:
    return {
        "AttributeId": urns.RECORD_MATCHING_POLICIES_ATTR,
        _VALUE_KEY: "true",
        "DataType": urns.STRING_DATATYPE,
        "IncludeInResult": "false",
    }


def deserialize_eval_response(
    response: httpx.Response,
    body: dict[str, object],
) -> EvalResponse:
    _check_top_level_status(response, body)
    raw_results = body["Response"]
    parsed: list[EvalResult] = []
    if isinstance(raw_results, list):
        _check_result_statuses(response, raw_results)
        parsed = [_parse_eval_result(entry) for entry in raw_results]
    return EvalResponse(eval_results=parsed)


_PermissionsBucket = tuple[str, list[ActionPermission]]


def deserialize_permissions_response(
    response: httpx.Response,
    body: dict[str, object],
) -> PermissionsResponse:
    _check_top_level_status(response, body)
    allowed: list[ActionPermission] = []
    denied: list[ActionPermission] = []
    dont_care: list[ActionPermission] = []
    buckets: list[_PermissionsBucket] = [
        ("allow", allowed),
        ("deny", denied),
        ("dontcare", dont_care),
    ]
    raw_results = body.get("Response")
    if isinstance(raw_results, list):
        _check_result_statuses(response, raw_results)
        _fill_permissions_buckets(raw_results, buckets)
    return PermissionsResponse(
        allowed=allowed,
        denied=denied,
        dont_care=dont_care,
    )


def _check_top_level_status(
    response: httpx.Response,
    body: dict[str, object],
) -> None:
    status = body.get("Status")
    if not isinstance(status, dict):
        return
    code, message = _extract_status_code_and_message(status)
    raise_if_not_ok(response, code=code, message=message)


def _check_result_statuses(
    response: httpx.Response,
    raw_results: list[object],
) -> None:
    for entry in raw_results:
        if not isinstance(entry, dict):
            continue
        status = entry.get("Status")
        if not isinstance(status, dict):
            continue
        code, message = _extract_status_code_and_message(status)
        raise_if_not_ok(response, code=code, message=message)


def _extract_status_code_and_message(
    status: dict[str, object],
) -> tuple[str, str]:
    status_code_raw = status.get("StatusCode")
    code = ""
    if isinstance(status_code_raw, dict):
        code = str(status_code_raw.get("Value", ""))
    message_raw = status.get("StatusMessage", "")
    message = str(message_raw) if message_raw else ""
    return code, message


def _fill_permissions_buckets(
    raw_results: list[object],
    buckets: list[_PermissionsBucket],
) -> None:
    for raw_result in raw_results:
        grouped = _extract_grouped(raw_result)
        if grouped is None:
            continue
        for key, target in buckets:
            for entry in _iter_bucket_items(grouped.get(key)):
                target.append(_parse_action_permission(entry))


def _extract_grouped(raw_result: object) -> dict[str, object] | None:
    if not isinstance(raw_result, dict):
        return None
    grouped = raw_result.get("ActionsAndObligations")
    if not isinstance(grouped, dict):
        return None
    return grouped


def _iter_bucket_items(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    return [entry for entry in raw if isinstance(entry, dict)]


def _parse_action_permission(entry: dict[str, object]) -> ActionPermission:
    obligations_raw = entry.get("Obligations", [])
    obligations = _parse_obligations(
        obligations_raw if isinstance(obligations_raw, list) else [],
    )
    matching_raw = entry.get("MatchingPolicies", [])
    policy_refs: list[PolicyRef] = []
    if isinstance(matching_raw, list):
        policy_refs = [
            PolicyRef(id=str(pid)) for pid in matching_raw if isinstance(pid, str)
        ]
    return ActionPermission(
        name=str(entry.get("Action", "")),
        obligations=obligations,
        policy_refs=policy_refs,
    )


def _serialize_subject(subject: Subject) -> dict[str, object]:
    pairs: list[AttrPair] = [(urns.SUBJECT_ID, subject.id)]
    pairs.extend(_collect_extra_attrs(subject.model_extra, urns.SUBJECT_PREFIX))
    pairs.extend(_collect_dict_attrs(subject.attributes))
    return _build_category(urns.SUBJECT_CATEGORY, pairs)


def _serialize_resource(resource: Resource) -> dict[str, object]:
    pairs: list[AttrPair] = [
        (urns.RESOURCE_ID, resource.id),
        (urns.RESOURCE_TYPE, resource.type),
    ]
    if resource.dimension is not None:
        pairs.append((urns.RESOURCE_DIMENSION, resource.dimension.value))
    if resource.nocache:
        pairs.append((urns.RESOURCE_NOCACHE, True))
    pairs.extend(_collect_extra_attrs(resource.model_extra, urns.RESOURCE_PREFIX))
    pairs.extend(_collect_dict_attrs(resource.attributes))
    return _build_category(urns.RESOURCE_CATEGORY, pairs)


def _serialize_action(action: Action) -> dict[str, object]:
    return _build_category(
        urns.ACTION_CATEGORY,
        [(urns.ACTION_ID, action.id)],
    )


def _serialize_application(application: Application) -> dict[str, object]:
    pairs: list[AttrPair] = [(urns.APPLICATION_ID, application.id)]
    pairs.extend(
        _collect_extra_attrs(application.model_extra, urns.APPLICATION_PREFIX),
    )
    pairs.extend(_collect_dict_attrs(application.attributes))
    return _build_category(urns.APPLICATION_CATEGORY, pairs)


def _serialize_environment(environment: Environment) -> dict[str, object]:
    pairs: list[AttrPair] = []
    pairs.extend(
        _collect_extra_attrs(environment.model_extra, urns.ENVIRONMENT_PREFIX),
    )
    pairs.extend(_collect_dict_attrs(environment.attributes))
    return _build_category(urns.ENVIRONMENT_CATEGORY, pairs)


def _build_category(
    category_id: str,
    pairs: list[AttrPair],
) -> dict[str, object]:
    attrs = [_make_attr(attr_id, attr_val) for attr_id, attr_val in pairs]
    return {
        _CATEGORY_ID_KEY: category_id,
        _ATTRIBUTE_KEY: attrs,
    }


def _make_attr(
    attr_id: str,
    attr_value: str | int | float | bool,
) -> dict[str, object]:
    return {
        "AttributeId": attr_id,
        _VALUE_KEY: attr_value,
        "DataType": _infer_datatype(attr_value),
        "IncludeInResult": "false",
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
    detail = _stringify_status_detail(raw.get("StatusDetail"))
    return Status(code=code_value, message=message, detail=detail)


def _stringify_status_detail(raw: object) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        return ", ".join(_stringify_status_detail(entry) for entry in raw if entry)
    if isinstance(raw, dict):
        parts: list[str] = []
        for child in raw.values():
            piece = _stringify_status_detail(child)
            if piece:
                parts.append(piece)
        return ", ".join(parts)
    return str(raw)


def _parse_obligations(
    raw_obligations: list[object],
) -> list[Obligation]:
    obligations: list[Obligation] = []
    for raw in raw_obligations:
        if not isinstance(raw, dict):
            continue
        attrs = [
            ObligationAttribute(
                id=str(assignment["AttributeId"]),
                attr_value=_stringify_assignment_value(assignment[_VALUE_KEY]),
            )
            for assignment in raw.get("AttributeAssignment", [])
            if isinstance(assignment, dict)
        ]
        obligations.append(Obligation(id=str(raw["Id"]), attributes=attrs))
    return obligations


def _stringify_assignment_value(raw: object) -> str:
    if isinstance(raw, list):
        return ", ".join(str(element) for element in raw)
    return str(raw)


def _parse_policy_refs(raw: dict[str, object]) -> list[PolicyRef]:
    policy_id_list = raw.get("PolicyIdentifierList", {})
    if not isinstance(policy_id_list, dict):
        return []
    raw_refs = policy_id_list.get("PolicyIdReference", [])
    if not isinstance(raw_refs, list):
        return []
    refs: list[PolicyRef] = []
    for ref_item in raw_refs:
        if not isinstance(ref_item, dict):
            continue
        refs.append(
            PolicyRef(
                id=str(ref_item["Id"]),
                version=str(ref_item.get("Version", "")),
            ),
        )
    return refs
