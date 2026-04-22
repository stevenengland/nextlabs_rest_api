from __future__ import annotations

import pytest

from nextlabs_sdk._pdp._enums import Decision
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


def test_status_code_only_and_with_message():
    s1 = Status(code="urn:oasis:names:tc:xacml:1.0:status:ok")
    assert s1.code == "urn:oasis:names:tc:xacml:1.0:status:ok"
    assert s1.message == ""
    assert s1.detail == ""

    s2 = Status(code="ok", message="Success")
    assert s2.message == "Success"
    assert s2.detail == ""


def test_status_with_detail():
    s = Status(
        code="urn:oasis:names:tc:xacml:1.0:status:missing-attribute",
        message="One or more required params are missing",
        detail="Service, Version",
    )
    assert s.detail == "Service, Version"


def test_obligation_attribute_fields():
    attr = ObligationAttribute(id="log-level", attr_value="info")
    assert attr.id == "log-level"
    assert attr.attr_value == "info"


def test_obligation_with_and_without_attributes():
    empty = Obligation(id="obl-1")
    assert empty.attributes == []

    full = Obligation(
        id="obligation-1",
        attributes=[ObligationAttribute(id="key", attr_value="val")],
    )
    assert full.id == "obligation-1"
    assert len(full.attributes) == 1
    assert full.attributes[0].id == "key"


def test_policy_ref_explicit_and_default_version():
    ref = PolicyRef(id="allow-view-policy", version="1.0")
    assert ref.id == "allow-view-policy"
    assert ref.version == "1.0"
    assert PolicyRef(id="p1").version == ""


def test_eval_result_permit_defaults():
    result = EvalResult(
        decision=Decision.PERMIT,
        status=Status(code="urn:oasis:names:tc:xacml:1.0:status:ok"),
    )
    assert result.decision == Decision.PERMIT
    assert result.obligations == []
    assert result.policy_refs == []


def test_eval_result_with_obligations_and_policies():
    result = EvalResult(
        decision=Decision.DENY,
        status=Status(code="urn:oasis:names:tc:xacml:1.0:status:ok"),
        obligations=[
            Obligation(
                id="log",
                attributes=[ObligationAttribute(id="level", attr_value="warn")],
            ),
        ],
        policy_refs=[PolicyRef(id="deny-policy", version="2.0")],
    )
    assert result.decision == Decision.DENY
    assert len(result.obligations) == 1
    assert result.obligations[0].id == "log"
    assert len(result.policy_refs) == 1
    assert result.policy_refs[0].id == "deny-policy"


def test_eval_response_first_result_and_empty():
    response = EvalResponse(
        eval_results=[
            EvalResult(decision=Decision.PERMIT, status=Status(code="ok")),
        ],
    )
    assert response.first_result.decision == Decision.PERMIT

    with pytest.raises(IndexError):
        EvalResponse(eval_results=[]).first_result


def test_action_permission_fields():
    perm = ActionPermission(name="VIEW", policy_refs=[PolicyRef(id="view-policy")])
    assert perm.name == "VIEW"
    assert len(perm.policy_refs) == 1


def test_permissions_response_groups_and_defaults():
    response = PermissionsResponse(
        allowed=[ActionPermission(name="VIEW")],
        denied=[ActionPermission(name="DELETE")],
        dont_care=[ActionPermission(name="ARCHIVE")],
    )
    assert len(response.allowed) == 1
    assert response.allowed[0].name == "VIEW"
    assert len(response.denied) == 1
    assert response.denied[0].name == "DELETE"
    assert len(response.dont_care) == 1

    empty = PermissionsResponse()
    assert empty.allowed == []
    assert empty.denied == []
    assert empty.dont_care == []
