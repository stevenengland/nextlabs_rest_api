from __future__ import annotations

from typing import Any, cast

from nextlabs_sdk._pdp._enums import Decision, ResourceDimension
from nextlabs_sdk._pdp._json_serializer import (
    deserialize_eval_response,
    deserialize_permissions_response,
    serialize_eval_request,
    serialize_permissions_request,
)
from nextlabs_sdk._pdp._request_models import (
    Action,
    Application,
    Environment,
    EvalRequest,
    PermissionsRequest,
    Resource,
    Subject,
)
from nextlabs_sdk._pdp import _urns as urns


def _find_category(body: Any, category_id: str) -> dict[str, object]:
    categories = body["Request"]
    if not isinstance(categories, dict):
        msg = f"Category {category_id} not found"
        raise AssertionError(msg)
    cat_list = categories["Category"]
    if not isinstance(cat_list, list):
        msg = f"Category {category_id} not found"
        raise AssertionError(msg)
    for cat in cat_list:
        if isinstance(cat, dict) and cat["CategoryId"] == category_id:
            return cat
    msg = f"Category {category_id} not found"
    raise AssertionError(msg)


def _find_attribute(category: Any, attr_id: str) -> dict[str, object]:
    attrs = category["Attribute"]
    if not isinstance(attrs, list):
        msg = f"Attribute {attr_id} not found"
        raise AssertionError(msg)
    for attr in attrs:
        if isinstance(attr, dict) and attr["AttributeId"] == attr_id:
            return attr
    msg = f"Attribute {attr_id} not found"
    raise AssertionError(msg)


def test_serialize_minimal_eval_request() -> None:
    request = EvalRequest(
        subject=Subject(id="user@example.com"),
        action=Action(id="VIEW"),
        resource=Resource(id="doc:1", type="documents"),
        application=Application(id="my-app"),
    )

    body_raw = serialize_eval_request(request)
    body = cast(dict[str, Any], body_raw)

    assert body["Request"]["ReturnPolicyIdList"] is False
    subject_cat = _find_category(body, urns.SUBJECT_CATEGORY)
    attr = _find_attribute(subject_cat, urns.SUBJECT_ID)
    assert attr["Value"] == "user@example.com"
    assert attr["DataType"] == urns.STRING_DATATYPE

    action_cat = _find_category(body, urns.ACTION_CATEGORY)
    assert _find_attribute(action_cat, urns.ACTION_ID)["Value"] == "VIEW"

    resource_cat = _find_category(body, urns.RESOURCE_CATEGORY)
    assert _find_attribute(resource_cat, urns.RESOURCE_ID)["Value"] == "doc:1"
    assert _find_attribute(resource_cat, urns.RESOURCE_TYPE)["Value"] == "documents"

    app_cat = _find_category(body, urns.APPLICATION_CATEGORY)
    assert _find_attribute(app_cat, urns.APPLICATION_ID)["Value"] == "my-app"


def test_serialize_return_policy_ids() -> None:
    request = EvalRequest(
        subject=Subject(id="u"),
        action=Action(id="a"),
        resource=Resource(id="r", type="t"),
        application=Application(id="app"),
        return_policy_ids=True,
    )

    body_raw = serialize_eval_request(request)
    body = cast(dict[str, Any], body_raw)

    assert body["Request"]["ReturnPolicyIdList"] is True


def test_serialize_subject_extra_kwargs_auto_prefixed() -> None:
    request = EvalRequest(
        subject=Subject(id="u", department="IT", level=3),
        action=Action(id="a"),
        resource=Resource(id="r", type="t"),
        application=Application(id="app"),
    )

    body_raw = serialize_eval_request(request)
    body = cast(dict[str, Any], body_raw)
    subject_cat = _find_category(body, urns.SUBJECT_CATEGORY)

    dept = _find_attribute(subject_cat, f"{urns.SUBJECT_PREFIX}department")
    assert dept["Value"] == "IT"
    assert dept["DataType"] == urns.STRING_DATATYPE

    level = _find_attribute(subject_cat, f"{urns.SUBJECT_PREFIX}level")
    assert level["Value"] == 3
    assert level["DataType"] == urns.INTEGER_DATATYPE


def test_serialize_subject_attributes_dict_not_prefixed() -> None:
    request = EvalRequest(
        subject=Subject(
            id="u",
            attributes={"custom:vendor:field": "value"},
        ),
        action=Action(id="a"),
        resource=Resource(id="r", type="t"),
        application=Application(id="app"),
    )

    body_raw = serialize_eval_request(request)
    body = cast(dict[str, Any], body_raw)
    subject_cat = _find_category(body, urns.SUBJECT_CATEGORY)

    custom = _find_attribute(subject_cat, "custom:vendor:field")
    assert custom["Value"] == "value"


def test_serialize_resource_dimension_and_nocache() -> None:
    request = EvalRequest(
        subject=Subject(id="u"),
        action=Action(id="a"),
        resource=Resource(
            id="r",
            type="t",
            dimension=ResourceDimension.FROM,
            nocache=True,
        ),
        application=Application(id="app"),
    )

    body_raw = serialize_eval_request(request)
    body = cast(dict[str, Any], body_raw)
    resource_cat = _find_category(body, urns.RESOURCE_CATEGORY)

    dim = _find_attribute(resource_cat, urns.RESOURCE_DIMENSION)
    assert dim["Value"] == "from"

    nc = _find_attribute(resource_cat, urns.RESOURCE_NOCACHE)
    assert nc["Value"] is True
    assert nc["DataType"] == urns.BOOLEAN_DATATYPE


def test_serialize_resource_extra_kwargs_auto_prefixed() -> None:
    request = EvalRequest(
        subject=Subject(id="u"),
        action=Action(id="a"),
        resource=Resource(id="r", type="t", category="security"),
        application=Application(id="app"),
    )

    body_raw = serialize_eval_request(request)
    body = cast(dict[str, Any], body_raw)
    resource_cat = _find_category(body, urns.RESOURCE_CATEGORY)
    cat_attr = _find_attribute(resource_cat, f"{urns.RESOURCE_PREFIX}category")
    assert cat_attr["Value"] == "security"


def test_serialize_application_extra_kwargs() -> None:
    request = EvalRequest(
        subject=Subject(id="u"),
        action=Action(id="a"),
        resource=Resource(id="r", type="t"),
        application=Application(id="app", version="2.0"),
    )

    body_raw = serialize_eval_request(request)
    body = cast(dict[str, Any], body_raw)
    app_cat = _find_category(body, urns.APPLICATION_CATEGORY)
    ver = _find_attribute(app_cat, f"{urns.APPLICATION_PREFIX}version")
    assert ver["Value"] == "2.0"


def test_serialize_environment() -> None:
    request = EvalRequest(
        subject=Subject(id="u"),
        action=Action(id="a"),
        resource=Resource(id="r", type="t"),
        application=Application(id="app"),
        environment=Environment(
            attributes={"ip": "10.0.0.1"},
            time_of_day="morning",
        ),
    )

    body_raw = serialize_eval_request(request)
    body = cast(dict[str, Any], body_raw)
    env_cat = _find_category(body, urns.ENVIRONMENT_CATEGORY)
    ip_attr = _find_attribute(env_cat, "ip")
    assert ip_attr["Value"] == "10.0.0.1"
    tod = _find_attribute(env_cat, f"{urns.ENVIRONMENT_PREFIX}time_of_day")
    assert tod["Value"] == "morning"


def test_serialize_no_environment_category_when_none() -> None:
    request = EvalRequest(
        subject=Subject(id="u"),
        action=Action(id="a"),
        resource=Resource(id="r", type="t"),
        application=Application(id="app"),
    )

    body_raw = serialize_eval_request(request)
    body = cast(dict[str, Any], body_raw)
    category_ids = [c["CategoryId"] for c in body["Request"]["Category"]]
    assert urns.ENVIRONMENT_CATEGORY not in category_ids


def test_serialize_permissions_request_no_action_category() -> None:
    request = PermissionsRequest(
        subject=Subject(id="u"),
        resource=Resource(id="r", type="t"),
        application=Application(id="app"),
    )

    body_raw = serialize_permissions_request(request)
    body = cast(dict[str, Any], body_raw)
    category_ids = [c["CategoryId"] for c in body["Request"]["Category"]]
    assert urns.ACTION_CATEGORY not in category_ids


def test_serialize_permissions_request_with_record_matching() -> None:
    request = PermissionsRequest(
        subject=Subject(id="u"),
        resource=Resource(id="r", type="t"),
        application=Application(id="app"),
        record_matching_policies=True,
    )

    body_raw = serialize_permissions_request(request)
    body = cast(dict[str, Any], body_raw)
    assert body["Request"]["RecordMatchingPolicies"] is True


def test_serialize_data_type_float() -> None:
    expected_score = 9.5
    request = EvalRequest(
        subject=Subject(id="u", score=expected_score),
        action=Action(id="a"),
        resource=Resource(id="r", type="t"),
        application=Application(id="app"),
    )

    body_raw = serialize_eval_request(request)
    body = cast(dict[str, Any], body_raw)
    subject_cat = _find_category(body, urns.SUBJECT_CATEGORY)
    score = _find_attribute(subject_cat, f"{urns.SUBJECT_PREFIX}score")
    assert score["Value"] == expected_score
    assert score["DataType"] == urns.DOUBLE_DATATYPE


def test_deserialize_permit_eval_response() -> None:
    body = {
        "Response": [
            {
                "Decision": "Permit",
                "Status": {
                    "StatusCode": {
                        "Value": "urn:oasis:names:tc:xacml:1.0:status:ok",
                    },
                },
            },
        ],
    }

    response = deserialize_eval_response(cast(dict[str, object], body))

    assert len(response.eval_results) == 1
    assert response.first_result.decision == Decision.PERMIT
    assert response.first_result.status.code == "urn:oasis:names:tc:xacml:1.0:status:ok"
    assert response.first_result.obligations == []
    assert response.first_result.policy_refs == []


def test_deserialize_deny_with_obligations() -> None:
    body = {
        "Response": [
            {
                "Decision": "Deny",
                "Status": {
                    "StatusCode": {
                        "Value": "urn:oasis:names:tc:xacml:1.0:status:ok",
                    },
                },
                "Obligations": [
                    {
                        "Id": "log-access",
                        "AttributeAssignment": [
                            {
                                "AttributeId": "log-level",
                                "Value": "warn",
                            },
                        ],
                    },
                ],
            },
        ],
    }

    response = deserialize_eval_response(cast(dict[str, object], body))

    assert response.first_result.decision == Decision.DENY
    assert len(response.first_result.obligations) == 1
    assert response.first_result.obligations[0].id == "log-access"
    assert response.first_result.obligations[0].attributes[0].id == "log-level"
    assert response.first_result.obligations[0].attributes[0].attr_value == "warn"


def test_deserialize_with_policy_refs() -> None:
    body = {
        "Response": [
            {
                "Decision": "Permit",
                "Status": {
                    "StatusCode": {"Value": "ok"},
                },
                "PolicyIdentifierList": {
                    "PolicyIdReference": [
                        {"Id": "allow-view", "Version": "1.0"},
                        {"Id": "allow-edit", "Version": "2.0"},
                    ],
                },
            },
        ],
    }

    response = deserialize_eval_response(cast(dict[str, object], body))

    assert len(response.first_result.policy_refs) == 2
    assert response.first_result.policy_refs[0].id == "allow-view"
    assert response.first_result.policy_refs[0].version == "1.0"
    assert response.first_result.policy_refs[1].id == "allow-edit"


def test_deserialize_with_status_message() -> None:
    body = {
        "Response": [
            {
                "Decision": "Indeterminate",
                "Status": {
                    "StatusCode": {"Value": "processing-error"},
                    "StatusMessage": "Policy evaluation error",
                },
            },
        ],
    }

    response = deserialize_eval_response(cast(dict[str, object], body))

    assert response.first_result.decision == Decision.INDETERMINATE
    assert response.first_result.status.message == "Policy evaluation error"


def test_deserialize_permissions_response() -> None:
    body = {
        "Response": [
            {
                "Decision": "Permit",
                "Status": {"StatusCode": {"Value": "ok"}},
                "Obligations": [],
                "Category": [
                    {
                        "CategoryId": "urn:oasis:names:tc:xacml:3.0:attribute-category:action",
                        "Attribute": [
                            {
                                "AttributeId": "urn:oasis:names:tc:xacml:1.0:action:action-id",
                                "Value": "VIEW",
                            },
                        ],
                    },
                ],
            },
            {
                "Decision": "Deny",
                "Status": {"StatusCode": {"Value": "ok"}},
                "Category": [
                    {
                        "CategoryId": "urn:oasis:names:tc:xacml:3.0:attribute-category:action",
                        "Attribute": [
                            {
                                "AttributeId": "urn:oasis:names:tc:xacml:1.0:action:action-id",
                                "Value": "DELETE",
                            },
                        ],
                    },
                ],
            },
            {
                "Decision": "NotApplicable",
                "Status": {"StatusCode": {"Value": "ok"}},
                "Category": [
                    {
                        "CategoryId": "urn:oasis:names:tc:xacml:3.0:attribute-category:action",
                        "Attribute": [
                            {
                                "AttributeId": "urn:oasis:names:tc:xacml:1.0:action:action-id",
                                "Value": "ARCHIVE",
                            },
                        ],
                    },
                ],
            },
        ],
    }

    response = deserialize_permissions_response(cast(dict[str, object], body))

    assert len(response.allowed) == 1
    assert response.allowed[0].name == "VIEW"
    assert len(response.denied) == 1
    assert response.denied[0].name == "DELETE"
    assert len(response.dont_care) == 1
    assert response.dont_care[0].name == "ARCHIVE"
