from __future__ import annotations

from xml.etree import ElementTree as ET

import httpx
import pytest

from nextlabs_sdk._pdp._enums import Decision
from nextlabs_sdk._pdp._request_models import (
    Action,
    Application,
    EvalRequest,
    PermissionsRequest,
    Resource,
    Subject,
)
from nextlabs_sdk._pdp._urns import (
    ACTION_CATEGORY,
    ACTION_ID,
    APPLICATION_CATEGORY,
    RESOURCE_CATEGORY,
    SUBJECT_CATEGORY,
    SUBJECT_ID,
)
from nextlabs_sdk._pdp._xml_serializer import (
    deserialize_eval_response,
    deserialize_permissions_response,
    serialize_eval_request,
    serialize_permissions_request,
)
from nextlabs_sdk.exceptions import PdpStatusError

XACML_NS = "urn:oasis:names:tc:xacml:3.0:core:schema:wd-17"
_OK_URN = "urn:oasis:names:tc:xacml:1.0:status:ok"


def _fake_response() -> httpx.Response:
    request = httpx.Request("POST", "https://pdp.example/dpc/authorization/pdp")
    return httpx.Response(200, request=request, content=b"")


def _parse_xml(data: bytes) -> ET.Element:
    return ET.fromstring(data)


def _ns(tag: str) -> str:
    return f"{{{XACML_NS}}}{tag}"


def _make_eval_request(return_policy_ids: bool = False) -> EvalRequest:
    return EvalRequest(
        subject=Subject(id="user@example.com"),
        action=Action(id="VIEW"),
        resource=Resource(id="doc:1", type="documents"),
        application=Application(id="my-app"),
        return_policy_ids=return_policy_ids,
    )


def test_xml_serialize_minimal_eval_request():
    root = _parse_xml(serialize_eval_request(_make_eval_request()))

    assert root.tag == _ns("Request")
    assert root.attrib["ReturnPolicyIdList"] == "false"
    category_ids = [el.attrib["Category"] for el in root.findall(_ns("Attributes"))]
    for cat in (
        SUBJECT_CATEGORY,
        ACTION_CATEGORY,
        RESOURCE_CATEGORY,
        APPLICATION_CATEGORY,
    ):
        assert cat in category_ids


@pytest.mark.parametrize(
    "return_policy_ids,expected",
    [
        pytest.param(False, "false", id="default-false"),
        pytest.param(True, "true", id="explicit-true"),
    ],
)
def test_xml_serialize_return_policy_ids(return_policy_ids: bool, expected: str):
    root = _parse_xml(
        serialize_eval_request(_make_eval_request(return_policy_ids=return_policy_ids)),
    )
    assert root.attrib["ReturnPolicyIdList"] == expected


def test_xml_serialize_subject_attribute_values():
    root = _parse_xml(serialize_eval_request(_make_eval_request()))

    for attrs_el in root.findall(_ns("Attributes")):
        if attrs_el.attrib["Category"] == SUBJECT_CATEGORY:
            attr_el = attrs_el.find(_ns("Attribute"))
            assert attr_el is not None
            assert attr_el.attrib["AttributeId"] == SUBJECT_ID
            value_el = attr_el.find(_ns("AttributeValue"))
            assert value_el is not None
            assert value_el.text == "user@example.com"
            return
    raise AssertionError("Subject category not found")


def test_xml_serialize_permissions_no_action():
    request = PermissionsRequest(
        subject=Subject(id="u"),
        resource=Resource(id="r", type="t"),
        application=Application(id="app"),
    )
    root = _parse_xml(serialize_permissions_request(request))

    category_ids = [el.attrib["Category"] for el in root.findall(_ns("Attributes"))]
    assert ACTION_CATEGORY not in category_ids


def test_xml_serialize_permissions_with_record_matching_policies():
    request = PermissionsRequest(
        subject=Subject(id="u"),
        resource=Resource(id="r", type="t"),
        application=Application(id="app"),
        record_matching_policies=True,
    )
    root = _parse_xml(serialize_permissions_request(request))

    env_el = _find_env_attributes(root)
    record_attr = _find_attribute_by_id(
        env_el, "nextlabs-record-matching-policies-in-result"
    )
    assert record_attr.get("IncludeInResult") == "false"
    value_el = record_attr.find(_ns("AttributeValue"))
    assert value_el is not None
    assert value_el.text == "true"
    assert value_el.get("DataType") == "http://www.w3.org/2001/XMLSchema#string"


def _find_env_attributes(root: ET.Element) -> ET.Element:
    for attrs_el in root.findall(_ns("Attributes")):
        if attrs_el.attrib["Category"] == (
            "urn:oasis:names:tc:xacml:3.0:attribute-category:environment"
        ):
            return attrs_el
    raise AssertionError("Environment Attributes element not found")


def _find_attribute_by_id(parent: ET.Element, attr_id: str) -> ET.Element:
    for attr_el in parent.findall(_ns("Attribute")):
        if attr_el.get("AttributeId") == attr_id:
            return attr_el
    raise AssertionError(f"Attribute {attr_id} not found")


def test_xml_deserialize_permit_response():
    xml_data = (
        f'<Response xmlns="{XACML_NS}">'
        f"<Result>"
        f"<Decision>Permit</Decision>"
        f'<Status><StatusCode Value="urn:oasis:names:tc:xacml:1.0:status:ok"/>'
        f"</Status>"
        f"</Result>"
        f"</Response>"
    ).encode()

    response = deserialize_eval_response(_fake_response(), xml_data)

    assert len(response.eval_results) == 1
    assert response.first_result.decision == Decision.PERMIT


def test_xml_deserialize_with_obligations():
    xml_data = (
        f'<Response xmlns="{XACML_NS}">'
        f"<Result>"
        f"<Decision>Deny</Decision>"
        f'<Status><StatusCode Value="urn:oasis:names:tc:xacml:1.0:status:ok"/>'
        f"</Status>"
        f"<Obligations>"
        f'<Obligation ObligationId="log">'
        f'<AttributeAssignment AttributeId="level">'
        f"warn</AttributeAssignment>"
        f"</Obligation>"
        f"</Obligations>"
        f"</Result>"
        f"</Response>"
    ).encode()

    response = deserialize_eval_response(_fake_response(), xml_data)

    assert response.first_result.decision == Decision.DENY
    assert len(response.first_result.obligations) == 1
    assert response.first_result.obligations[0].id == "log"
    assert response.first_result.obligations[0].attributes[0].attr_value == "warn"


def test_xml_deserialize_raises_on_non_ok_status_with_detail():
    xml_data = (
        f'<Response xmlns="{XACML_NS}">'
        f"<Result>"
        f"<Decision>Indeterminate</Decision>"
        f"<Status>"
        f'<StatusCode Value="urn:oasis:names:tc:xacml:1.0:status:missing-attribute"/>'
        f"<StatusMessage>One or more required params are missing</StatusMessage>"
        f"<StatusDetail>Service, Version</StatusDetail>"
        f"</Status>"
        f"</Result>"
        f"</Response>"
    ).encode()

    with pytest.raises(PdpStatusError) as excinfo:
        deserialize_eval_response(_fake_response(), xml_data)

    assert excinfo.value.xacml_status_code == (
        "urn:oasis:names:tc:xacml:1.0:status:missing-attribute"
    )
    assert "missing" in excinfo.value.xacml_status_message


def test_xml_deserialize_raises_on_non_ok_permissions_result():
    xml_data = (
        f'<Response xmlns="{XACML_NS}">'
        f"<Result>"
        f"<Decision>Indeterminate</Decision>"
        f'<Status><StatusCode Value="processing-error"/>'
        f"<StatusMessage>broken</StatusMessage></Status>"
        f"</Result>"
        f"</Response>"
    ).encode()

    with pytest.raises(PdpStatusError) as excinfo:
        deserialize_permissions_response(_fake_response(), xml_data)

    assert excinfo.value.xacml_status_code == "processing-error"


def test_xml_deserialize_without_status_detail_defaults_empty():
    xml_data = (
        f'<Response xmlns="{XACML_NS}">'
        f"<Result>"
        f"<Decision>Permit</Decision>"
        f'<Status><StatusCode Value="{_OK_URN}"/></Status>'
        f"</Result>"
        f"</Response>"
    ).encode()

    response = deserialize_eval_response(_fake_response(), xml_data)

    assert response.first_result.status.detail == ""


def test_xml_deserialize_permissions_response():
    def _result(decision: str, action: str) -> str:
        return (
            f"<Result>"
            f"<Decision>{decision}</Decision>"
            f'<Status><StatusCode Value="{_OK_URN}"/></Status>'
            f'<Attributes Category="{ACTION_CATEGORY}">'
            f'<Attribute AttributeId="{ACTION_ID}">'
            f"<AttributeValue>{action}</AttributeValue>"
            f"</Attribute>"
            f"</Attributes>"
            f"</Result>"
        )

    xml_data = (
        f'<Response xmlns="{XACML_NS}">'
        f'{_result("Permit", "VIEW")}{_result("Deny", "DELETE")}'
        f"</Response>"
    ).encode()

    response = deserialize_permissions_response(_fake_response(), xml_data)

    assert len(response.allowed) == 1
    assert response.allowed[0].name == "VIEW"
    assert len(response.denied) == 1
    assert response.denied[0].name == "DELETE"
