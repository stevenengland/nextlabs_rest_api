from __future__ import annotations

import json
from typing import Any

import pytest
from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._pdp import (
    ActionPermission,
    Decision,
    EvalResponse,
    EvalResult,
    Obligation,
    ObligationAttribute,
    PdpClient,
    PermissionsResponse,
    PolicyRef,
    Status,
)

runner = CliRunner()

_GLOBAL_OPTS = (
    "--base-url",
    "https://example.com",
    "--pdp-url",
    "https://pdp.example.com",
    "--client-secret",
    "my-secret",
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

_PERMS_ARGS = (
    "pdp",
    "permissions",
    "--subject",
    "user1",
    "--resource",
    "doc1",
    "--resource-type",
    "file",
)


def _stub_client() -> Any:
    mock_client = mock(PdpClient)
    when(_client_factory).make_pdp_client(...).thenReturn(mock_client)
    return mock_client


def _eval_response(
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


def _perm_response(
    allowed: list[ActionPermission] | None = None,
    denied: list[ActionPermission] | None = None,
    dont_care: list[ActionPermission] | None = None,
) -> PermissionsResponse:
    return PermissionsResponse(
        allowed=allowed or [],
        denied=denied or [],
        dont_care=dont_care or [],
    )


# --- eval output variants ---


@pytest.mark.parametrize(
    "decision,extra_flags,expected_text",
    [
        pytest.param(Decision.PERMIT, (), "Permit", id="permit"),
        pytest.param(Decision.DENY, (), "Deny", id="deny"),
    ],
)
def test_pdp_eval_decision(
    decision: Decision,
    extra_flags: tuple[str, ...],
    expected_text: str,
) -> None:
    mock_client = _stub_client()
    when(mock_client).evaluate(...).thenReturn(_eval_response(decision))
    result = runner.invoke(app, [*_GLOBAL_OPTS, *_EVAL_ARGS, *extra_flags])
    assert result.exit_code == 0
    assert expected_text in result.output


def test_pdp_eval_json() -> None:
    mock_client = _stub_client()
    when(mock_client).evaluate(...).thenReturn(_eval_response(Decision.PERMIT))
    result = runner.invoke(app, [*_GLOBAL_OPTS, "--output", "json", *_EVAL_ARGS])
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
    when(mock_client).evaluate(...).thenReturn(_eval_response(obligations=obligations))
    result = runner.invoke(app, [*_GLOBAL_OPTS, *_EVAL_ARGS])
    assert result.exit_code == 0
    assert "log-obligation" in result.output
    assert "log-level" in result.output


def test_pdp_eval_with_policy_refs() -> None:
    mock_client = _stub_client()
    refs = [PolicyRef(id="AllowITAccess", version="1.0")]
    when(mock_client).evaluate(...).thenReturn(_eval_response(policy_refs=refs))
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, *_EVAL_ARGS, "--return-policy-ids"],
    )
    assert result.exit_code == 0
    assert "AllowITAccess" in result.output


def _eval_response_with_status(
    decision: Decision, code: str, message: str, detail: str
) -> EvalResponse:
    return EvalResponse(
        eval_results=[
            EvalResult(
                decision=decision,
                status=Status(code=code, message=message, detail=detail),
            ),
        ],
    )


def test_pdp_eval_renders_status_detail_when_present() -> None:
    mock_client = _stub_client()
    response = _eval_response_with_status(
        decision=Decision.INDETERMINATE,
        code="urn:oasis:names:tc:xacml:1.0:status:missing-attribute",
        message="One or more required params are missing",
        detail="Service, Version",
    )
    when(mock_client).evaluate(...).thenReturn(response)

    result = runner.invoke(app, [*_GLOBAL_OPTS, *_EVAL_ARGS])

    assert result.exit_code == 0
    assert "One or more required params are missing" in result.output
    assert "Detail:" in result.output
    assert "Service, Version" in result.output


def test_pdp_eval_omits_detail_line_when_empty() -> None:
    mock_client = _stub_client()
    when(mock_client).evaluate(...).thenReturn(_eval_response(Decision.PERMIT))

    result = runner.invoke(app, [*_GLOBAL_OPTS, *_EVAL_ARGS])

    assert result.exit_code == 0
    assert "Detail:" not in result.output


def test_pdp_eval_renders_status_with_bracket_chars_literally() -> None:
    mock_client = _stub_client()
    response = _eval_response_with_status(
        decision=Decision.INDETERMINATE,
        code="missing-attribute",
        message="missing [Service] attribute",
        detail="[policy:secret] Service, Version",
    )
    when(mock_client).evaluate(...).thenReturn(response)

    result = runner.invoke(app, [*_GLOBAL_OPTS, *_EVAL_ARGS])

    assert result.exit_code == 0
    assert "[Service]" in result.output
    assert "[policy:secret]" in result.output


@pytest.mark.parametrize(
    "extra_args",
    [
        pytest.param(
            (
                "--subject-attr",
                "dept=IT",
                "--resource-attr",
                "classification=public",
            ),
            id="with-attributes",
        ),
        pytest.param(("--content-type", "xml"), id="xml-content-type"),
    ],
)
def test_pdp_eval_extra_flags(extra_args: tuple[str, ...]) -> None:
    mock_client = _stub_client()
    when(mock_client).evaluate(...).thenReturn(_eval_response())
    result = runner.invoke(app, [*_GLOBAL_OPTS, *_EVAL_ARGS, *extra_args])
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
            "--pdp-url",
            "https://pdp.example.com",
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


# --- permissions output variants ---


def test_pdp_permissions_allowed() -> None:
    mock_client = _stub_client()
    when(mock_client).permissions(...).thenReturn(
        _perm_response(
            allowed=[ActionPermission(name="VIEW"), ActionPermission(name="EDIT")],
        )
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, *_PERMS_ARGS])
    assert result.exit_code == 0
    assert "VIEW" in result.output
    assert "EDIT" in result.output
    assert "Allowed" in result.output


def test_pdp_permissions_denied() -> None:
    mock_client = _stub_client()
    when(mock_client).permissions(...).thenReturn(
        _perm_response(
            denied=[ActionPermission(name="DELETE")],
        )
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, *_PERMS_ARGS])
    assert result.exit_code == 0
    assert "DELETE" in result.output
    assert "Denied" in result.output


def test_pdp_permissions_json() -> None:
    mock_client = _stub_client()
    when(mock_client).permissions(...).thenReturn(
        _perm_response(
            allowed=[ActionPermission(name="VIEW")],
        )
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, "--output", "json", *_PERMS_ARGS])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["allowed"][0]["name"] == "VIEW"


def test_pdp_permissions_with_matching_policies() -> None:
    mock_client = _stub_client()
    when(mock_client).permissions(...).thenReturn(
        _perm_response(
            allowed=[
                ActionPermission(
                    name="VIEW",
                    policy_refs=[PolicyRef(id="AllowAll", version="1.0")],
                ),
            ],
        )
    )
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, *_PERMS_ARGS, "--record-matching-policies"],
    )
    assert result.exit_code == 0
    assert "VIEW" in result.output


def test_pdp_permissions_empty() -> None:
    mock_client = _stub_client()
    when(mock_client).permissions(...).thenReturn(_perm_response())
    result = runner.invoke(app, [*_GLOBAL_OPTS, *_PERMS_ARGS])
    assert result.exit_code == 0


# --- output format dispatch ---


@pytest.mark.parametrize(
    "fmt",
    ["table", "wide", "detail"],
)
def test_pdp_eval_non_json_formats_show_sections(fmt: str) -> None:
    mock_client = _stub_client()
    obligations = [
        Obligation(
            id="log-obligation",
            attributes=[ObligationAttribute(id="log-level", attr_value="info")],
        ),
    ]
    refs = [PolicyRef(id="AllowAll", version="1.0")]
    when(mock_client).evaluate(...).thenReturn(
        _eval_response(obligations=obligations, policy_refs=refs),
    )
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--output", fmt, *_EVAL_ARGS, "--return-policy-ids"],
    )
    assert result.exit_code == 0
    assert "Decision:" in result.output
    assert "Permit" in result.output
    assert "Obligations" in result.output
    assert "Matched Policies" in result.output


def test_pdp_eval_json_format_returns_parseable_json() -> None:
    mock_client = _stub_client()
    when(mock_client).evaluate(...).thenReturn(_eval_response(Decision.PERMIT))
    result = runner.invoke(app, [*_GLOBAL_OPTS, "--output", "json", *_EVAL_ARGS])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["eval_results"][0]["decision"] == "Permit"


@pytest.mark.parametrize(
    "fmt",
    ["table", "wide", "detail"],
)
def test_pdp_permissions_non_json_formats_show_sections(fmt: str) -> None:
    mock_client = _stub_client()
    when(mock_client).permissions(...).thenReturn(
        _perm_response(
            allowed=[ActionPermission(name="VIEW")],
            denied=[ActionPermission(name="DELETE")],
        ),
    )
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--output", fmt, *_PERMS_ARGS],
    )
    assert result.exit_code == 0
    assert "Allowed" in result.output
    assert "VIEW" in result.output
    assert "Denied" in result.output
    assert "DELETE" in result.output


def test_pdp_permissions_json_format_returns_parseable_json() -> None:
    mock_client = _stub_client()
    when(mock_client).permissions(...).thenReturn(
        _perm_response(allowed=[ActionPermission(name="VIEW")]),
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, "--output", "json", *_PERMS_ARGS])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["allowed"][0]["name"] == "VIEW"


# --- pdp explain ---


def _write_eval_payload(tmp_path: Any) -> Any:
    payload = (
        '{"subject":{"id":"u"},"action":{"id":"VIEW"},'
        '"resource":{"id":"r","type":"doc"},"application":{"id":"app"}}'
    )
    path = tmp_path / "eval.json"
    path.write_text(payload, encoding="utf-8")
    return path


def _explain_args(payload_path: Any) -> tuple[str, ...]:
    return ("pdp", "explain", "--payload", str(payload_path))


def test_pdp_explain_renders_allowed_with_policies(tmp_path: Any) -> None:
    mock_client = _stub_client()
    response = _perm_response(
        allowed=[
            ActionPermission(
                name="VIEW",
                policy_refs=[PolicyRef(id="ROOT/VIEW Policy")],
            ),
        ],
        denied=[
            ActionPermission(
                name="DELETE",
                policy_refs=[PolicyRef(id="ROOT/DELETE Policy")],
            ),
        ],
    )
    when(mock_client).permissions(...).thenReturn(response)

    path = _write_eval_payload(tmp_path)
    result = runner.invoke(app, [*_GLOBAL_OPTS, *_explain_args(path)])

    assert result.exit_code == 0
    assert "Allowed" in result.output
    assert "VIEW" in result.output
    assert "ROOT/VIEW Policy" in result.output
    assert "Denied" in result.output
    assert "DELETE" in result.output


def test_pdp_explain_sets_record_matching_policies_and_drops_action(
    tmp_path: Any,
) -> None:
    mock_client = _stub_client()
    captured: dict[str, Any] = {}

    def _capture(request: Any, *, content_type: Any) -> PermissionsResponse:
        captured["request"] = request
        captured["content_type"] = content_type
        return _perm_response()

    when(mock_client).permissions(...).thenAnswer(_capture)

    path = _write_eval_payload(tmp_path)
    result = runner.invoke(app, [*_GLOBAL_OPTS, *_explain_args(path)])

    assert result.exit_code == 0
    request = captured["request"]
    assert request.record_matching_policies is True
    assert not hasattr(request, "action")


def test_pdp_explain_action_filter_prints_matching_bucket(tmp_path: Any) -> None:
    mock_client = _stub_client()
    when(mock_client).permissions(...).thenReturn(
        _perm_response(
            allowed=[ActionPermission(name="VIEW")],
            denied=[ActionPermission(name="DELETE")],
        ),
    )

    path = _write_eval_payload(tmp_path)
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, *_explain_args(path), "--action", "DELETE"],
    )

    assert result.exit_code == 0
    assert "Denied" in result.output
    assert "DELETE" in result.output
    assert "VIEW" not in result.output


def test_pdp_explain_action_filter_missing_action_still_succeeds(
    tmp_path: Any,
) -> None:
    mock_client = _stub_client()
    when(mock_client).permissions(...).thenReturn(
        _perm_response(allowed=[ActionPermission(name="VIEW")]),
    )

    path = _write_eval_payload(tmp_path)
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, *_explain_args(path), "--action", "OPEN"],
    )

    assert result.exit_code == 0
    assert "OPEN" in result.output
    assert "not found" in result.output


def test_pdp_explain_empty_hint_when_no_matching_policies(tmp_path: Any) -> None:
    mock_client = _stub_client()
    when(mock_client).permissions(...).thenReturn(
        _perm_response(allowed=[ActionPermission(name="VIEW")]),
    )

    path = _write_eval_payload(tmp_path)
    result = runner.invoke(app, [*_GLOBAL_OPTS, *_explain_args(path)])

    assert result.exit_code == 0
    assert "record_matching_policies" in result.output


def test_pdp_explain_json_output(tmp_path: Any) -> None:
    mock_client = _stub_client()
    when(mock_client).permissions(...).thenReturn(
        _perm_response(
            allowed=[
                ActionPermission(
                    name="VIEW",
                    policy_refs=[PolicyRef(id="P1")],
                ),
            ],
        ),
    )

    path = _write_eval_payload(tmp_path)
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--output", "json", *_explain_args(path)],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["allowed"][0]["name"] == "VIEW"
    assert parsed["allowed"][0]["policy_refs"][0]["id"] == "P1"


def test_pdp_explain_surfaces_pdp_status_error(tmp_path: Any) -> None:
    from nextlabs_sdk.exceptions import PdpStatusError

    mock_client = _stub_client()
    when(mock_client).permissions(...).thenRaise(
        PdpStatusError(
            "Invalid Request :: One or more mandatory attributes are missing",
            xacml_status_code=("urn:oasis:names:tc:xacml:1.0:status:missing-attribute"),
            xacml_status_message=(
                "Invalid Request :: One or more mandatory attributes are missing"
            ),
            status_code=200,
            request_method="POST",
            request_url="https://pdp.example.com/dpc/authorization/pdppermissions",
        ),
    )

    path = _write_eval_payload(tmp_path)
    result = runner.invoke(app, [*_GLOBAL_OPTS, *_explain_args(path)])

    assert result.exit_code == 1
    assert "PDP rejected the request" in result.output
    assert "mandatory attributes" in result.output


def test_pdp_explain_verbose_pdp_status_error_shows_xacml_code(tmp_path: Any) -> None:
    from strip_ansi import strip_ansi

    from nextlabs_sdk.exceptions import PdpStatusError

    urn = "urn:oasis:names:tc:xacml:1.0:status:missing-attribute"
    mock_client = _stub_client()
    when(mock_client).permissions(...).thenRaise(
        PdpStatusError(
            "missing attrs",
            xacml_status_code=urn,
            xacml_status_message="missing attrs",
            status_code=200,
            request_method="POST",
            request_url="https://pdp.example.com/dpc/authorization/pdppermissions",
            response_body='{"Status":{}}',
        ),
    )

    path = _write_eval_payload(tmp_path)
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "-v", *_explain_args(path)],
        terminal_width=240,
    )

    assert result.exit_code == 1
    assert "PDP rejected the request" in result.output
    stderr_plain = strip_ansi(result.stderr)
    assert urn in stderr_plain
    assert "envelope" in stderr_plain
