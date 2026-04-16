from __future__ import annotations

from xml.etree import ElementTree as ET

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

XACML_NS = "urn:oasis:names:tc:xacml:3.0:core:schema:wd-17"


def _parse_xml(data: bytes) -> ET.Element:
    return ET.fromstring(data)


def _ns(tag: str) -> str:
    return f"{{{XACML_NS}}}{tag}"


def test_xml_serialize_minimal_eval_request() -> None:
    request = EvalRequest(
        subject=Subject(id="user@example.com"),
        action=Action(id="VIEW"),
        resource=Resource(id="doc:1", type="documents"),
        application=Application(id="my-app"),
    )

    xml_bytes = serialize_eval_request(request)
    root = _parse_xml(xml_bytes)

    assert root.tag == _ns("Request")
    assert root.attrib["ReturnPolicyIdList"] == "false"

    attributes_elements = root.findall(_ns("Attributes"))
    category_ids = [el.attrib["Category"] for el in attributes_elements]
    assert SUBJECT_CATEGORY in category_ids
    assert ACTION_CATEGORY in category_ids
    assert RESOURCE_CATEGORY in category_ids
    assert APPLICATION_CATEGORY in category_ids


def test_xml_serialize_return_policy_ids_true() -> None:
    request = EvalRequest(
        subject=Subject(id="u"),
        action=Action(id="a"),
        resource=Resource(id="r", type="t"),
        application=Application(id="app"),
        return_policy_ids=True,
    )

    xml_bytes = serialize_eval_request(request)
    root = _parse_xml(xml_bytes)

    assert root.attrib["ReturnPolicyIdList"] == "true"


def test_xml_serialize_subject_attribute_values() -> None:
    request = EvalRequest(
        subject=Subject(id="user@example.com"),
        action=Action(id="VIEW"),
        resource=Resource(id="r", type="t"),
        application=Application(id="app"),
    )

    xml_bytes = serialize_eval_request(request)
    root = _parse_xml(xml_bytes)

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


def test_xml_serialize_permissions_no_action() -> None:
    request = PermissionsRequest(
        subject=Subject(id="u"),
        resource=Resource(id="r", type="t"),
        application=Application(id="app"),
    )

    xml_bytes = serialize_permissions_request(request)
    root = _parse_xml(xml_bytes)

    category_ids = [el.attrib["Category"] for el in root.findall(_ns("Attributes"))]
    assert ACTION_CATEGORY not in category_ids


def test_xml_deserialize_permit_response() -> None:
    xml_data = (
        f'<Response xmlns="{XACML_NS}">'
        f"<Result>"
        f"<Decision>Permit</Decision>"
        f"<Status><StatusCode "
        f'Value="urn:oasis:names:tc:xacml:1.0:status:ok"/>'
        f"</Status>"
        f"</Result>"
        f"</Response>"
    ).encode()

    response = deserialize_eval_response(xml_data)

    assert len(response.results) == 1
    assert response.result.decision == Decision.PERMIT


def test_xml_deserialize_with_obligations() -> None:
    xml_data = (
        f'<Response xmlns="{XACML_NS}">'
        f"<Result>"
        f"<Decision>Deny</Decision>"
        f"<Status><StatusCode "
        f'Value="urn:oasis:names:tc:xacml:1.0:status:ok"/>'
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

    response = deserialize_eval_response(xml_data)

    assert response.result.decision == Decision.DENY
    assert len(response.result.obligations) == 1
    assert response.result.obligations[0].id == "log"
    assert response.result.obligations[0].attributes[0].value == "warn"


def test_xml_deserialize_permissions_response() -> None:
    xml_data = (
        f'<Response xmlns="{XACML_NS}">'
        f"<Result>"
        f"<Decision>Permit</Decision>"
        f"<Status><StatusCode "
        f'Value="ok"/></Status>'
        f"<Attributes "
        f'Category="{ACTION_CATEGORY}">'
        f'<Attribute AttributeId="{ACTION_ID}">'
        f"<AttributeValue>VIEW</AttributeValue>"
        f"</Attribute>"
        f"</Attributes>"
        f"</Result>"
        f"<Result>"
        f"<Decision>Deny</Decision>"
        f"<Status><StatusCode "
        f'Value="ok"/></Status>'
        f"<Attributes "
        f'Category="{ACTION_CATEGORY}">'
        f'<Attribute AttributeId="{ACTION_ID}">'
        f"<AttributeValue>DELETE</AttributeValue>"
        f"</Attribute>"
        f"</Attributes>"
        f"</Result>"
        f"</Response>"
    ).encode()

    response = deserialize_permissions_response(xml_data)

    assert len(response.allowed) == 1
    assert response.allowed[0].name == "VIEW"
    assert len(response.denied) == 1
    assert response.denied[0].name == "DELETE"
