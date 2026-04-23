from __future__ import annotations

from xml.etree import ElementTree as ET

import httpx
from defusedxml import ElementTree as DefusedET

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

_XACML_NS = "urn:oasis:names:tc:xacml:3.0:core:schema:wd-17"
_ATTRIBUTE_TAG = "Attribute"
_ATTRIBUTE_VALUE_TAG = "AttributeValue"
_ATTRIBUTE_ID_KEY = "AttributeId"


def serialize_eval_request(request: EvalRequest) -> bytes:
    root = _make_request_element(request.return_policy_ids)
    _add_subject(root, request.subject)
    _add_action(root, request.action)
    _add_resource(root, request.resource)
    _add_application(root, request.application)
    if request.environment is not None:
        _add_environment(root, request.environment)
    return ET.tostring(root, encoding="unicode").encode("utf-8")


def serialize_permissions_request(request: PermissionsRequest) -> bytes:
    root = _make_request_element(request.return_policy_ids)
    _add_subject(root, request.subject)
    _add_resource(root, request.resource)
    _add_application(root, request.application)
    _add_permissions_environment(
        root,
        request.environment,
        record_matching_policies=request.record_matching_policies,
    )
    return ET.tostring(root, encoding="unicode").encode("utf-8")


def _add_permissions_environment(
    parent: ET.Element,
    environment: Environment | None,
    *,
    record_matching_policies: bool,
) -> None:
    if environment is None and not record_matching_policies:
        return
    attrs: list[AttrPair] = []
    if environment is not None:
        attrs.extend(
            _collect_extra_attrs(environment.model_extra, urns.ENVIRONMENT_PREFIX),
        )
        attrs.extend(_collect_dict_attrs(environment.attributes))
    attrs_el = ET.SubElement(parent, _ns("Attributes"))
    attrs_el.set("Category", urns.ENVIRONMENT_CATEGORY)
    for attr_id, attr_value in attrs:
        _append_attribute(attrs_el, attr_id, attr_value)
    if record_matching_policies:
        _append_record_matching_attribute(attrs_el)


def _append_attribute(
    parent: ET.Element,
    attr_id: str,
    attr_value: AttrValue,
) -> None:
    attr_el = ET.SubElement(parent, _ns(_ATTRIBUTE_TAG))
    attr_el.set("IncludeInResult", "false")
    attr_el.set(_ATTRIBUTE_ID_KEY, attr_id)
    value_el = ET.SubElement(attr_el, _ns(_ATTRIBUTE_VALUE_TAG))
    value_el.set("DataType", _infer_datatype(attr_value))
    value_el.text = _serialize_value(attr_value)


def _append_record_matching_attribute(parent: ET.Element) -> None:
    attr_el = ET.SubElement(parent, _ns(_ATTRIBUTE_TAG))
    attr_el.set(_ATTRIBUTE_ID_KEY, urns.RECORD_MATCHING_POLICIES_ATTR)
    attr_el.set("IncludeInResult", "false")
    value_el = ET.SubElement(attr_el, _ns(_ATTRIBUTE_VALUE_TAG))
    value_el.set("DataType", urns.STRING_DATATYPE)
    value_el.text = "true"


def deserialize_eval_response(
    response: httpx.Response,
    body: bytes,
) -> EvalResponse:
    root = DefusedET.fromstring(body)
    result_els = root.findall(_ns("Result"))
    _raise_on_non_ok_result(response, result_els)
    parsed = [_parse_result(result_el) for result_el in result_els]
    return EvalResponse(eval_results=parsed)


def deserialize_permissions_response(
    response: httpx.Response,
    body: bytes,
) -> PermissionsResponse:
    root = DefusedET.fromstring(body)
    result_els = root.findall(_ns("Result"))
    _raise_on_non_ok_result(response, result_els)
    allowed: list[ActionPermission] = []
    denied: list[ActionPermission] = []
    dont_care: list[ActionPermission] = []

    for result_el in result_els:
        action_name = _extract_action_name_xml(result_el)
        obligations = _parse_obligations_xml(result_el)
        policy_refs = _parse_policy_refs_xml(result_el)
        permission = ActionPermission(
            name=action_name,
            obligations=obligations,
            policy_refs=policy_refs,
        )

        decision_text = result_el.findtext(_ns("Decision"), "")
        decision = Decision(decision_text)
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


def _raise_on_non_ok_result(
    response: httpx.Response,
    result_els: list[ET.Element],
) -> None:
    for result_el in result_els:
        status = _parse_status_xml(result_el)
        raise_if_not_ok(response, code=status.code, message=status.message)


def _ns(tag: str) -> str:
    return f"{{{_XACML_NS}}}{tag}"


def _make_request_element(return_policy_ids: bool) -> ET.Element:
    ET.register_namespace("", _XACML_NS)
    root = ET.Element(_ns("Request"))
    root.set(
        "ReturnPolicyIdList",
        "true" if return_policy_ids else "false",
    )
    return root


def _add_attributes_element(
    parent: ET.Element,
    category: str,
    attrs: list[AttrPair],
) -> None:
    attrs_el = ET.SubElement(parent, _ns("Attributes"))
    attrs_el.set("Category", category)
    for attr_id, attr_value in attrs:
        _append_attribute(attrs_el, attr_id, attr_value)


AttrValue = str | int | float | bool
AttrPair = tuple[str, AttrValue]


def _coerce_attr(raw: object) -> AttrValue:
    if isinstance(raw, (str, int, float, bool)):
        return raw
    return str(raw)


def _collect_extra_attrs(
    model_extra: dict[str, object] | None,
    prefix: str,
) -> list[AttrPair]:
    collected: list[AttrPair] = []
    for key, attr_value in (model_extra or {}).items():
        collected.append((f"{prefix}{key}", _coerce_attr(attr_value)))
    return collected


def _collect_dict_attrs(
    attributes: dict[str, str | int | float | bool],
) -> list[AttrPair]:
    return list(attributes.items())


def _add_subject(parent: ET.Element, subject: Subject) -> None:
    attrs: list[AttrPair] = [(urns.SUBJECT_ID, subject.id)]
    attrs.extend(_collect_extra_attrs(subject.model_extra, urns.SUBJECT_PREFIX))
    attrs.extend(_collect_dict_attrs(subject.attributes))
    _add_attributes_element(parent, urns.SUBJECT_CATEGORY, attrs)


def _add_resource(parent: ET.Element, resource: Resource) -> None:
    attrs: list[AttrPair] = [
        (urns.RESOURCE_ID, resource.id),
        (urns.RESOURCE_TYPE, resource.type),
    ]
    if resource.dimension is not None:
        attrs.append((urns.RESOURCE_DIMENSION, resource.dimension.value))
    if resource.nocache:
        attrs.append((urns.RESOURCE_NOCACHE, True))
    attrs.extend(_collect_extra_attrs(resource.model_extra, urns.RESOURCE_PREFIX))
    attrs.extend(_collect_dict_attrs(resource.attributes))
    _add_attributes_element(parent, urns.RESOURCE_CATEGORY, attrs)


def _add_action(parent: ET.Element, action: Action) -> None:
    _add_attributes_element(
        parent,
        urns.ACTION_CATEGORY,
        [(urns.ACTION_ID, action.id)],
    )


def _add_application(parent: ET.Element, application: Application) -> None:
    attrs: list[AttrPair] = [(urns.APPLICATION_ID, application.id)]
    attrs.extend(
        _collect_extra_attrs(application.model_extra, urns.APPLICATION_PREFIX),
    )
    attrs.extend(_collect_dict_attrs(application.attributes))
    _add_attributes_element(parent, urns.APPLICATION_CATEGORY, attrs)


def _add_environment(
    parent: ET.Element,
    environment: Environment,
) -> None:
    attrs: list[AttrPair] = []
    attrs.extend(
        _collect_extra_attrs(environment.model_extra, urns.ENVIRONMENT_PREFIX),
    )
    attrs.extend(_collect_dict_attrs(environment.attributes))
    _add_attributes_element(parent, urns.ENVIRONMENT_CATEGORY, attrs)


def _infer_datatype(attr_value: str | int | float | bool) -> str:
    if isinstance(attr_value, bool):
        return urns.BOOLEAN_DATATYPE
    if isinstance(attr_value, int):
        return urns.INTEGER_DATATYPE
    if isinstance(attr_value, float):
        return urns.DOUBLE_DATATYPE
    return urns.STRING_DATATYPE


def _serialize_value(attr_value: str | int | float | bool) -> str:
    if isinstance(attr_value, bool):
        return str(attr_value).lower()
    return str(attr_value)


def _parse_result(result_el: ET.Element) -> EvalResult:
    decision_text = result_el.findtext(_ns("Decision"), "")
    decision = Decision(decision_text)
    status = _parse_status_xml(result_el)
    obligations = _parse_obligations_xml(result_el)
    policy_refs = _parse_policy_refs_xml(result_el)
    return EvalResult(
        decision=decision,
        status=status,
        obligations=obligations,
        policy_refs=policy_refs,
    )


def _parse_status_xml(result_el: ET.Element) -> Status:
    status_el = result_el.find(_ns("Status"))
    if status_el is None:
        return Status(code="")
    code_el = status_el.find(_ns("StatusCode"))
    code = ""
    if code_el is not None:
        code = code_el.get("Value", "") or ""
    message = status_el.findtext(_ns("StatusMessage"), "")
    detail = _read_status_detail(status_el)
    return Status(code=code, message=message, detail=detail)


def _read_status_detail(status_el: ET.Element) -> str:
    detail_el = status_el.find(_ns("StatusDetail"))
    if detail_el is None:
        return ""
    return "".join(detail_el.itertext()).strip()


def _parse_obligations_xml(result_el: ET.Element) -> list[Obligation]:
    obligations: list[Obligation] = []
    obligations_el = result_el.find(_ns("Obligations"))
    if obligations_el is None:
        return obligations
    for obl_el in obligations_el.findall(_ns("Obligation")):
        obl_id = obl_el.get("ObligationId", "")
        attrs = [
            ObligationAttribute(
                id=aa_el.get(_ATTRIBUTE_ID_KEY, ""),
                attr_value=(aa_el.text or "").strip(),
            )
            for aa_el in obl_el.findall(_ns("AttributeAssignment"))
        ]
        obligations.append(Obligation(id=obl_id, attributes=attrs))
    return obligations


def _parse_policy_refs_xml(result_el: ET.Element) -> list[PolicyRef]:
    refs: list[PolicyRef] = []
    pid_list = result_el.find(_ns("PolicyIdentifierList"))
    if pid_list is None:
        return refs
    for ref_el in pid_list.findall(_ns("PolicyIdReference")):
        refs.append(
            PolicyRef(
                id=ref_el.text or "",
                version=ref_el.get("Version", ""),
            )
        )
    return refs


def _find_action_value_el(result_el: ET.Element) -> ET.Element | None:
    for attrs_el in result_el.findall(_ns("Attributes")):
        if attrs_el.get("Category") != urns.ACTION_CATEGORY:
            continue
        for attr_el in attrs_el.findall(_ns(_ATTRIBUTE_TAG)):
            if attr_el.get(_ATTRIBUTE_ID_KEY) == urns.ACTION_ID:
                return attr_el.find(_ns(_ATTRIBUTE_VALUE_TAG))
    return None


def _extract_action_name_xml(result_el: ET.Element) -> str:
    value_el = _find_action_value_el(result_el)
    if value_el is not None and value_el.text:
        return value_el.text
    return ""
