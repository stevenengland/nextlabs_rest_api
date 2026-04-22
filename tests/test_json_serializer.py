from __future__ import annotations

from typing import Any, cast

import httpx
import pytest

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
from nextlabs_sdk.exceptions import PdpStatusError

_OK_URN = "urn:oasis:names:tc:xacml:1.0:status:ok"


def _fake_response() -> httpx.Response:
    request = httpx.Request("POST", "https://pdp.example/dpc/authorization/pdp")
    return httpx.Response(200, request=request, json={})


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
    assert "RecordMatchingPolicies" not in body["Request"]
    env_cat = _find_category(body, urns.ENVIRONMENT_CATEGORY)
    record_attr = _find_attribute(env_cat, urns.RECORD_MATCHING_POLICIES_ATTR)
    assert record_attr["Value"] == "true"
    assert record_attr["DataType"] == urns.STRING_DATATYPE
    assert record_attr["IncludeInResult"] is False


def test_serialize_permissions_request_merges_record_matching_into_env():
    body = _perm_body(
        PermissionsRequest(
            subject=Subject(id="u"),
            resource=Resource(id="r", type="t"),
            application=Application(id="app"),
            environment=Environment(attributes={"tenant": "acme"}),
            record_matching_policies=True,
        ),
    )
    env_cat = _find_category(body, urns.ENVIRONMENT_CATEGORY)
    assert _find_attribute(env_cat, "tenant")["Value"] == "acme"
    assert _find_attribute(env_cat, urns.RECORD_MATCHING_POLICIES_ATTR)


def test_serialize_permissions_request_no_env_when_disabled():
    body = _perm_body(
        PermissionsRequest(
            subject=Subject(id="u"),
            resource=Resource(id="r", type="t"),
            application=Application(id="app"),
        ),
    )
    category_ids = [c["CategoryId"] for c in body["Request"]["Category"]]
    assert urns.ENVIRONMENT_CATEGORY not in category_ids


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

    response = deserialize_eval_response(
        _fake_response(), cast(dict[str, object], body)
    )

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

    response = deserialize_eval_response(
        _fake_response(), cast(dict[str, object], body)
    )

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
                "Status": {"StatusCode": {"Value": _OK_URN}},
                "PolicyIdentifierList": {
                    "PolicyIdReference": [
                        {"Id": "allow-view", "Version": "1.0"},
                        {"Id": "allow-edit", "Version": "2.0"},
                    ],
                },
            },
        ],
    }

    response = deserialize_eval_response(
        _fake_response(), cast(dict[str, object], body)
    )

    assert len(response.first_result.policy_refs) == 2
    assert response.first_result.policy_refs[0].id == "allow-view"
    assert response.first_result.policy_refs[0].version == "1.0"
    assert response.first_result.policy_refs[1].id == "allow-edit"


def test_deserialize_raises_on_per_result_non_ok_status_with_message():
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

    with pytest.raises(PdpStatusError) as excinfo:
        deserialize_eval_response(_fake_response(), cast(dict[str, object], body))

    assert excinfo.value.xacml_status_code == "processing-error"
    assert excinfo.value.xacml_status_message == "Policy evaluation error"
    assert excinfo.value.message == "Policy evaluation error"


def test_deserialize_raises_on_missing_attribute_status_urn():
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

    with pytest.raises(PdpStatusError) as excinfo:
        deserialize_eval_response(_fake_response(), cast(dict[str, object], body))

    assert excinfo.value.xacml_status_code == (
        "urn:oasis:names:tc:xacml:1.0:status:missing-attribute"
    )
    assert "missing" in excinfo.value.message


def test_deserialize_raises_on_short_non_ok_status_code():
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

    with pytest.raises(PdpStatusError) as excinfo:
        deserialize_eval_response(_fake_response(), cast(dict[str, object], body))

    assert excinfo.value.xacml_status_code == "missing-attribute"


def test_deserialize_without_status_detail_defaults_empty():
    body = {
        "Response": [
            {
                "Decision": "Permit",
                "Status": {"StatusCode": {"Value": _OK_URN}},
            },
        ],
    }

    response = deserialize_eval_response(
        _fake_response(), cast(dict[str, object], body)
    )

    assert response.first_result.status.detail == ""


def test_deserialize_permissions_response():
    body = {
        "Status": {"StatusCode": {"Value": _OK_URN}},
        "Response": [
            {
                "ActionsAndObligations": {
                    "allow": [
                        {
                            "Action": "OPEN",
                            "MatchingPolicies": ["ROOT/OPEN Policy"],
                            "Obligations": [],
                        },
                        {
                            "Action": "SEND",
                            "MatchingPolicies": [
                                "ROOT/OPEN Policy",
                                "ROOT/SEND Policy",
                            ],
                            "Obligations": [
                                {
                                    "Id": "Obligation 1",
                                    "AttributeAssignment": [
                                        {
                                            "AttributeId": "arg1",
                                            "Value": ["val1"],
                                            "DataType": (
                                                "http://www.w3.org/2001/"
                                                "XMLSchema#string"
                                            ),
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                    "deny": [
                        {
                            "Action": "DELETE",
                            "MatchingPolicies": ["ROOT/DELETE Policy"],
                            "Obligations": [],
                        },
                    ],
                    "dontcare": [],
                },
            },
        ],
    }

    response = deserialize_permissions_response(
        _fake_response(), cast(dict[str, object], body)
    )

    assert [p.name for p in response.allowed] == ["OPEN", "SEND"]
    assert response.allowed[0].policy_refs[0].id == "ROOT/OPEN Policy"
    send = response.allowed[1]
    assert [ref.id for ref in send.policy_refs] == [
        "ROOT/OPEN Policy",
        "ROOT/SEND Policy",
    ]
    assert send.obligations[0].id == "Obligation 1"
    assert send.obligations[0].attributes[0].attr_value == "val1"
    assert [p.name for p in response.denied] == ["DELETE"]
    assert response.dont_care == []


def test_deserialize_permissions_response_tolerates_missing_actions_and_obligations():
    body = {"Status": {"StatusCode": {"Value": _OK_URN}}, "Response": [{}]}

    response = deserialize_permissions_response(
        _fake_response(), cast(dict[str, object], body)
    )

    assert response.allowed == []
    assert response.denied == []
    assert response.dont_care == []


def test_deserialize_permissions_response_tolerates_missing_response_key():
    body: dict[str, Any] = {"Status": {"StatusCode": {"Value": _OK_URN}}}

    response = deserialize_permissions_response(
        _fake_response(), cast(dict[str, object], body)
    )

    assert response.allowed == []


_MISSING_ATTR_URN = "urn:oasis:names:tc:xacml:1.0:status:missing-attribute"


def test_deserialize_permissions_response_raises_on_top_level_non_ok_status():
    body = {
        "Status": {
            "StatusMessage": (
                "Invalid Request :: One or more mandatory attributes are missing"
            ),
            "StatusCode": {"Value": _MISSING_ATTR_URN},
        },
        "Response": [
            {
                "Status": {
                    "StatusMessage": (
                        "Invalid Request :: One or more mandatory attributes are missing"
                    ),
                    "StatusCode": {"Value": _MISSING_ATTR_URN},
                },
                "ActionsAndObligations": {"allow": [], "deny": [], "dontcare": []},
            },
        ],
    }

    with pytest.raises(PdpStatusError) as excinfo:
        deserialize_permissions_response(
            _fake_response(),
            cast(dict[str, object], body),
        )

    assert excinfo.value.xacml_status_code == _MISSING_ATTR_URN
    assert "mandatory attributes are missing" in excinfo.value.xacml_status_message
    assert "mandatory attributes are missing" in excinfo.value.message


def test_deserialize_eval_response_raises_on_top_level_non_ok_status_without_decision():
    body = {
        "Status": {
            "StatusMessage": "Invalid Request :: missing attrs",
            "StatusCode": {"Value": _MISSING_ATTR_URN},
        },
        "Response": [
            {
                "Status": {
                    "StatusMessage": "Invalid Request :: missing attrs",
                    "StatusCode": {"Value": _MISSING_ATTR_URN},
                },
            },
        ],
    }

    with pytest.raises(PdpStatusError) as excinfo:
        deserialize_eval_response(_fake_response(), cast(dict[str, object], body))

    assert excinfo.value.xacml_status_code == _MISSING_ATTR_URN


def test_deserialize_permissions_response_raises_on_per_result_only_non_ok_status():
    body = {
        "Response": [
            {
                "Status": {
                    "StatusMessage": "missing attrs",
                    "StatusCode": {"Value": _MISSING_ATTR_URN},
                },
                "ActionsAndObligations": {"allow": [], "deny": [], "dontcare": []},
            },
        ],
    }

    with pytest.raises(PdpStatusError):
        deserialize_permissions_response(
            _fake_response(),
            cast(dict[str, object], body),
        )


def test_deserialize_carries_request_context_on_status_error():
    body = {
        "Status": {
            "StatusMessage": "bad",
            "StatusCode": {"Value": _MISSING_ATTR_URN},
        },
    }
    request = httpx.Request(
        "POST", "https://pdp.example/dpc/authorization/pdppermissions"
    )
    response = httpx.Response(200, request=request, json={})

    with pytest.raises(PdpStatusError) as excinfo:
        deserialize_permissions_response(response, cast(dict[str, object], body))

    assert excinfo.value.status_code == 200
    assert excinfo.value.request_method == "POST"
    assert excinfo.value.request_url == (
        "https://pdp.example/dpc/authorization/pdppermissions"
    )
    assert excinfo.value.envelope_status_code == _MISSING_ATTR_URN
