from __future__ import annotations

import json
from typing import Any

from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._pdp import (
    Decision,
    EvalResponse,
    EvalResult,
    Obligation,
    ObligationAttribute,
    PdpClient,
    PolicyRef,
    Status,
)

runner = CliRunner()

_GLOBAL_OPTS = (
    "--base-url",
    "https://example.com",
    "--client-secret",
    "my-secret",
)


def _stub_client() -> Any:
    mock_client = mock(PdpClient)
    when(_client_factory).make_pdp_client(...).thenReturn(mock_client)
    return mock_client


def _make_eval_response(
    decision: Decision = Decision.PERMIT,
    obligations: list[Obligation] | None = None,
    policy_refs: list[PolicyRef] | None = None,
) -> EvalResponse:
    return EvalResponse(
        eval_results=[
            EvalResult(
                decision=decision,
                status=Status(code="urn:oasis:names:tc:xacml:1.0:status:ok"),
                obligations=obligations or [],
                policy_refs=policy_refs or [],
            ),
        ],
    )


_EVAL_ARGS = (
    "pdp",
    "eval",
    "--subject",
    "user1",
    "--resource",
    "doc1",
    "--resource-type",
    "file",
    "--action",
    "VIEW",
)


def test_pdp_eval_permit() -> None:
    mock_client = _stub_client()
    when(mock_client).evaluate(...).thenReturn(_make_eval_response(Decision.PERMIT))
    result = runner.invoke(app, [*_GLOBAL_OPTS, *_EVAL_ARGS])
    assert result.exit_code == 0
    assert "Permit" in result.output


def test_pdp_eval_deny() -> None:
    mock_client = _stub_client()
    when(mock_client).evaluate(...).thenReturn(_make_eval_response(Decision.DENY))
    result = runner.invoke(app, [*_GLOBAL_OPTS, *_EVAL_ARGS])
    assert result.exit_code == 0
    assert "Deny" in result.output


def test_pdp_eval_json() -> None:
    mock_client = _stub_client()
    when(mock_client).evaluate(...).thenReturn(_make_eval_response(Decision.PERMIT))
    result = runner.invoke(app, [*_GLOBAL_OPTS, "--json", *_EVAL_ARGS])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["eval_results"][0]["decision"] == "Permit"


def test_pdp_eval_with_obligations() -> None:
    mock_client = _stub_client()
    obligations = [
        Obligation(
            id="log-obligation",
            attributes=[ObligationAttribute(id="log-level", attr_value="info")],
        ),
    ]
    when(mock_client).evaluate(...).thenReturn(
        _make_eval_response(obligations=obligations),
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, *_EVAL_ARGS])
    assert result.exit_code == 0
    assert "log-obligation" in result.output
    assert "log-level" in result.output


def test_pdp_eval_with_policy_refs() -> None:
    mock_client = _stub_client()
    refs = [PolicyRef(id="AllowITAccess", version="1.0")]
    when(mock_client).evaluate(...).thenReturn(
        _make_eval_response(policy_refs=refs),
    )
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, *_EVAL_ARGS, "--return-policy-ids"],
    )
    assert result.exit_code == 0
    assert "AllowITAccess" in result.output


def test_pdp_eval_with_attributes() -> None:
    mock_client = _stub_client()
    when(mock_client).evaluate(...).thenReturn(_make_eval_response())
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            *_EVAL_ARGS,
            "--subject-attr",
            "dept=IT",
            "--resource-attr",
            "classification=public",
        ],
    )
    assert result.exit_code == 0
    assert "Permit" in result.output


def test_pdp_eval_xml_content_type() -> None:
    mock_client = _stub_client()
    when(mock_client).evaluate(...).thenReturn(_make_eval_response())
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, *_EVAL_ARGS, "--content-type", "xml"],
    )
    assert result.exit_code == 0
    assert "Permit" in result.output


def test_pdp_eval_invalid_resource_dimension() -> None:
    _stub_client()
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, *_EVAL_ARGS, "--resource-dimension", "invalid"],
    )
    assert result.exit_code == 1
    assert "resource dimension" in result.output.lower()


def test_pdp_eval_missing_credentials() -> None:
    result = runner.invoke(
        app,
        [
            "--base-url",
            "https://example.com",
            "pdp",
            "eval",
            "--subject",
            "user1",
            "--resource",
            "doc1",
            "--resource-type",
            "file",
            "--action",
            "VIEW",
        ],
    )
    assert result.exit_code == 1
    assert "client-secret" in result.output.lower() or "CLIENT_SECRET" in result.output
