from __future__ import annotations

from nextlabs_sdk._pdp._enums import ContentType, Decision, ResourceDimension


def test_content_type_json_value() -> None:
    assert ContentType.JSON.value == "application/json"


def test_content_type_xml_value() -> None:
    assert ContentType.XML.value == "application/xml"


def test_decision_permit_value() -> None:
    assert Decision.PERMIT.value == "Permit"


def test_decision_deny_value() -> None:
    assert Decision.DENY.value == "Deny"


def test_decision_not_applicable_value() -> None:
    assert Decision.NOT_APPLICABLE.value == "NotApplicable"


def test_decision_indeterminate_value() -> None:
    assert Decision.INDETERMINATE.value == "Indeterminate"


def test_decision_from_string() -> None:
    assert Decision("Permit") is Decision.PERMIT


def test_resource_dimension_from_value() -> None:
    assert ResourceDimension.FROM.value == "from"
    assert ResourceDimension.TO.value == "to"
