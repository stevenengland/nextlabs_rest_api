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


def test_status_with_code_only() -> None:
    status = Status(code="urn:oasis:names:tc:xacml:1.0:status:ok")

    assert status.code == "urn:oasis:names:tc:xacml:1.0:status:ok"
    assert status.message == ""


def test_status_with_message() -> None:
    status = Status(code="ok", message="Success")

    assert status.message == "Success"


def test_obligation_attribute() -> None:
    attr = ObligationAttribute(id="log-level", attr_value="info")

    assert attr.id == "log-level"
    assert attr.attr_value == "info"


def test_obligation_with_attributes() -> None:
    obligation = Obligation(
        id="obligation-1",
        attributes=[
            ObligationAttribute(id="key", attr_value="val"),
        ],
    )

    assert obligation.id == "obligation-1"
    assert len(obligation.attributes) == 1
    assert obligation.attributes[0].id == "key"


def test_obligation_defaults_empty_attributes() -> None:
    obligation = Obligation(id="obl-1")

    assert obligation.attributes == []


def test_policy_ref() -> None:
    ref = PolicyRef(id="allow-view-policy", version="1.0")

    assert ref.id == "allow-view-policy"
    assert ref.version == "1.0"


def test_policy_ref_default_version() -> None:
    ref = PolicyRef(id="p1")

    assert ref.version == ""


def test_eval_result_permit() -> None:
    result = EvalResult(
        decision=Decision.PERMIT,
        status=Status(code="urn:oasis:names:tc:xacml:1.0:status:ok"),
    )

    assert result.decision == Decision.PERMIT
    assert result.obligations == []
    assert result.policy_refs == []


def test_eval_result_with_obligations_and_policies() -> None:
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


def test_eval_response_result_property() -> None:
    response = EvalResponse(
        eval_results=[
            EvalResult(
                decision=Decision.PERMIT,
                status=Status(code="ok"),
            ),
        ],
    )

    assert response.first_result.decision == Decision.PERMIT


def test_eval_response_result_raises_on_empty() -> None:
    response = EvalResponse(eval_results=[])

    with pytest.raises(IndexError):
        response.first_result


def test_action_permission() -> None:
    perm = ActionPermission(
        name="VIEW",
        policy_refs=[PolicyRef(id="view-policy")],
    )

    assert perm.name == "VIEW"
    assert len(perm.policy_refs) == 1


def test_permissions_response_groups() -> None:
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


def test_permissions_response_defaults_empty() -> None:
    response = PermissionsResponse()

    assert response.allowed == []
    assert response.denied == []
    assert response.dont_care == []
