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


def _eval_body(request: EvalRequest) -> dict[str, Any]:
    return cast(dict[str, Any], serialize_eval_request(request))


def _perm_body(request: PermissionsRequest) -> dict[str, Any]:
    return cast(dict[str, Any], serialize_permissions_request(request))


def _minimal_eval(**overrides: Any) -> EvalRequest:
    kwargs: dict[str, Any] = {
        "subject": Subject(id="u"),
        "action": Action(id="a"),
        "resource": Resource(id="r", type="t"),
        "application": Application(id="app"),
    }
    kwargs.update(overrides)
    return EvalRequest(**kwargs)


def test_serialize_minimal_eval_request():
    body = _eval_body(
        EvalRequest(
            subject=Subject(id="user@example.com"),
            action=Action(id="VIEW"),
            resource=Resource(id="doc:1", type="documents"),
            application=Application(id="my-app"),
        ),
    )

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


def test_serialize_return_policy_ids():
    body = _eval_body(_minimal_eval(return_policy_ids=True))

    assert body["Request"]["ReturnPolicyIdList"] is True


def test_serialize_subject_extra_kwargs_auto_prefixed():
    body = _eval_body(_minimal_eval(subject=Subject(id="u", department="IT", level=3)))
    subject_cat = _find_category(body, urns.SUBJECT_CATEGORY)

    dept = _find_attribute(subject_cat, f"{urns.SUBJECT_PREFIX}department")
    assert dept["Value"] == "IT"
    assert dept["DataType"] == urns.STRING_DATATYPE

    level = _find_attribute(subject_cat, f"{urns.SUBJECT_PREFIX}level")
    assert level["Value"] == 3
    assert level["DataType"] == urns.INTEGER_DATATYPE


def test_serialize_subject_attributes_dict_not_prefixed():
    body = _eval_body(
        _minimal_eval(
            subject=Subject(id="u", attributes={"custom:vendor:field": "value"})
        ),
    )
    subject_cat = _find_category(body, urns.SUBJECT_CATEGORY)

    custom = _find_attribute(subject_cat, "custom:vendor:field")
    assert custom["Value"] == "value"


def test_serialize_resource_dimension_and_nocache():
    body = _eval_body(
        _minimal_eval(
            resource=Resource(
                id="r",
                type="t",
                dimension=ResourceDimension.FROM,
                nocache=True,
            ),
        ),
    )
    resource_cat = _find_category(body, urns.RESOURCE_CATEGORY)

    dim = _find_attribute(resource_cat, urns.RESOURCE_DIMENSION)
    assert dim["Value"] == "from"

    nc = _find_attribute(resource_cat, urns.RESOURCE_NOCACHE)
    assert nc["Value"] is True
    assert nc["DataType"] == urns.BOOLEAN_DATATYPE


def test_serialize_resource_extra_kwargs_auto_prefixed():
    body = _eval_body(
        _minimal_eval(resource=Resource(id="r", type="t", category="security"))
    )
    resource_cat = _find_category(body, urns.RESOURCE_CATEGORY)
    cat_attr = _find_attribute(resource_cat, f"{urns.RESOURCE_PREFIX}category")
    assert cat_attr["Value"] == "security"


def test_serialize_application_extra_kwargs():
    body = _eval_body(_minimal_eval(application=Application(id="app", version="2.0")))
    app_cat = _find_category(body, urns.APPLICATION_CATEGORY)
    ver = _find_attribute(app_cat, f"{urns.APPLICATION_PREFIX}version")
    assert ver["Value"] == "2.0"


def test_serialize_environment():
    body = _eval_body(
        _minimal_eval(
            environment=Environment(
                attributes={"ip": "10.0.0.1"},
                time_of_day="morning",
            ),
        ),
    )
    env_cat = _find_category(body, urns.ENVIRONMENT_CATEGORY)
    ip_attr = _find_attribute(env_cat, "ip")
    assert ip_attr["Value"] == "10.0.0.1"
    tod = _find_attribute(env_cat, f"{urns.ENVIRONMENT_PREFIX}time_of_day")
    assert tod["Value"] == "morning"


def test_serialize_no_environment_category_when_none():
    body = _eval_body(_minimal_eval())
    category_ids = [c["CategoryId"] for c in body["Request"]["Category"]]
    assert urns.ENVIRONMENT_CATEGORY not in category_ids


def test_serialize_permissions_request_no_action_category():
    body = _perm_body(
        PermissionsRequest(
            subject=Subject(id="u"),
            resource=Resource(id="r", type="t"),
            application=Application(id="app"),
        ),
    )
    category_ids = [c["CategoryId"] for c in body["Request"]["Category"]]
    assert urns.ACTION_CATEGORY not in category_ids


def test_serialize_permissions_request_with_record_matching():
    body = _perm_body(
        PermissionsRequest(
            subject=Subject(id="u"),
            resource=Resource(id="r", type="t"),
            application=Application(id="app"),
            record_matching_policies=True,
        ),
    )
    assert body["Request"]["RecordMatchingPolicies"] is True


def test_serialize_data_type_float():
    expected_score = 9.5
    body = _eval_body(_minimal_eval(subject=Subject(id="u", score=expected_score)))
    subject_cat = _find_category(body, urns.SUBJECT_CATEGORY)
    score = _find_attribute(subject_cat, f"{urns.SUBJECT_PREFIX}score")
    assert score["Value"] == expected_score
    assert score["DataType"] == urns.DOUBLE_DATATYPE


def test_deserialize_permit_eval_response():
    body = {
        "Response": [
            {
                "Decision": "Permit",
                "Status": {
                    "StatusCode": {"Value": "urn:oasis:names:tc:xacml:1.0:status:ok"},
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


def test_deserialize_deny_with_obligations():
    body = {
        "Response": [
            {
                "Decision": "Deny",
                "Status": {
                    "StatusCode": {"Value": "urn:oasis:names:tc:xacml:1.0:status:ok"},
                },
                "Obligations": [
                    {
                        "Id": "log-access",
                        "AttributeAssignment": [
                            {"AttributeId": "log-level", "Value": "warn"},
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


def test_deserialize_with_policy_refs():
    body = {
        "Response": [
            {
                "Decision": "Permit",
                "Status": {"StatusCode": {"Value": "ok"}},
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


def test_deserialize_with_status_message():
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
    assert response.first_result.status.detail == ""


def test_deserialize_with_status_detail_string():
    body = {
        "Response": [
            {
                "Decision": "Indeterminate",
                "Status": {
                    "StatusCode": {
                        "Value": "urn:oasis:names:tc:xacml:1.0:status:missing-attribute",
                    },
                    "StatusMessage": "One or more required params are missing",
                    "StatusDetail": "Service, Version",
                },
            },
        ],
    }

    response = deserialize_eval_response(cast(dict[str, object], body))

    assert response.first_result.status.detail == "Service, Version"


def test_deserialize_with_status_detail_dict():
    body = {
        "Response": [
            {
                "Decision": "Indeterminate",
                "Status": {
                    "StatusCode": {"Value": "missing-attribute"},
                    "StatusDetail": {"MissingAttributeDetail": ["Service", "Version"]},
                },
            },
        ],
    }

    response = deserialize_eval_response(cast(dict[str, object], body))

    detail = response.first_result.status.detail
    assert "Service" in detail
    assert "Version" in detail


def test_deserialize_without_status_detail_defaults_empty():
    body = {
        "Response": [
            {
                "Decision": "Permit",
                "Status": {"StatusCode": {"Value": "ok"}},
            },
        ],
    }

    response = deserialize_eval_response(cast(dict[str, object], body))

    assert response.first_result.status.detail == ""


def test_deserialize_permissions_response():
    action_cat = "urn:oasis:names:tc:xacml:3.0:attribute-category:action"
    action_id = "urn:oasis:names:tc:xacml:1.0:action:action-id"

    def _entry(decision: str, value: str) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "Decision": decision,
            "Status": {"StatusCode": {"Value": "ok"}},
            "Category": [
                {
                    "CategoryId": action_cat,
                    "Attribute": [{"AttributeId": action_id, "Value": value}],
                },
            ],
        }
        if decision == "Permit":
            entry["Obligations"] = []
        return entry

    body = {
        "Response": [
            _entry("Permit", "VIEW"),
            _entry("Deny", "DELETE"),
            _entry("NotApplicable", "ARCHIVE"),
        ],
    }

    response = deserialize_permissions_response(cast(dict[str, object], body))

    assert len(response.allowed) == 1
    assert response.allowed[0].name == "VIEW"
    assert len(response.denied) == 1
    assert response.denied[0].name == "DELETE"
    assert len(response.dont_care) == 1
    assert response.dont_care[0].name == "ARCHIVE"
