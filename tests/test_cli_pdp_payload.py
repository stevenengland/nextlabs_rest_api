"""Integration tests for PDP CLI ``--payload`` / ``--payload-format`` options."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mockito import ANY, mock, verify, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._pdp import (
    Decision,
    EvalResponse,
    EvalResult,
    PdpClient,
    PermissionsResponse,
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


def _structured_eval() -> dict[str, Any]:
    return {
        "subject": {"id": "user@example.com"},
        "action": {"id": "VIEW"},
        "resource": {"id": "doc:1", "type": "documents"},
        "application": {"id": "my-app"},
    }


def _structured_perm() -> dict[str, Any]:
    return {
        "subject": {"id": "user@example.com"},
        "resource": {"id": "doc:1", "type": "documents"},
        "application": {"id": "my-app"},
    }


def _raw_xacml() -> dict[str, Any]:
    return {
        "Request": {
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
    }


def _stub_client() -> Any:
    mock_client = mock(PdpClient)
    when(_client_factory).make_pdp_client(...).thenReturn(mock_client)
    return mock_client


def _permit_eval() -> EvalResponse:
    return EvalResponse(
        eval_results=[
            EvalResult(
                decision=Decision.PERMIT,
                status=Status(code="ok"),
                obligations=[],
                policy_refs=[],
            ),
        ],
    )


def _permit_perm() -> PermissionsResponse:
    return PermissionsResponse(allowed=[], denied=[], dont_care=[])


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_eval_payload_structured_json(tmp_path: Path) -> None:
    mock_client = _stub_client()
    when(mock_client).evaluate(...).thenReturn(_permit_eval())
    path = _write(tmp_path, "p.json", json.dumps(_structured_eval()))

    result = runner.invoke(app, [*_GLOBAL_OPTS, "pdp", "eval", "--payload", str(path)])

    assert result.exit_code == 0, result.output
    assert "Permit" in result.output
    verify(mock_client).evaluate(ANY, content_type=ANY)


def test_eval_payload_structured_yaml(tmp_path: Path) -> None:
    mock_client = _stub_client()
    when(mock_client).evaluate(...).thenReturn(_permit_eval())
    yaml_text = (
        "subject:\n  id: user@example.com\n"
        "action:\n  id: VIEW\n"
        "resource:\n  id: doc:1\n  type: documents\n"
        "application:\n  id: my-app\n"
    )
    path = _write(tmp_path, "p.yaml", yaml_text)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "pdp", "eval", "--payload", str(path)])

    assert result.exit_code == 0, result.output


def test_eval_payload_raw_xacml_dispatches_evaluate_raw(tmp_path: Path) -> None:
    mock_client = _stub_client()
    when(mock_client).evaluate_raw(...).thenReturn(_permit_eval())
    path = _write(tmp_path, "x.json", json.dumps(_raw_xacml()))

    result = runner.invoke(app, [*_GLOBAL_OPTS, "pdp", "eval", "--payload", str(path)])

    assert result.exit_code == 0, result.output
    verify(mock_client).evaluate_raw(_raw_xacml())


def test_eval_payload_conflicts_with_flags(tmp_path: Path) -> None:
    _stub_client()
    path = _write(tmp_path, "p.json", json.dumps(_structured_eval()))

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "pdp",
            "eval",
            "--payload",
            str(path),
            "--subject",
            "u1",
        ],
    )

    assert result.exit_code != 0
    assert "--payload cannot be combined" in result.output
    assert "--subject" in result.output


def test_eval_payload_missing_file(tmp_path: Path) -> None:
    _stub_client()
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "pdp",
            "eval",
            "--payload",
            str(tmp_path / "nope.json"),
        ],
    )
    assert result.exit_code != 0
    assert "Payload file not found" in result.output


def test_eval_payload_format_override_xacml(tmp_path: Path) -> None:
    mock_client = _stub_client()
    when(mock_client).evaluate_raw(...).thenReturn(_permit_eval())
    path = _write(tmp_path, "x.json", json.dumps(_raw_xacml()))

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "pdp",
            "eval",
            "--payload",
            str(path),
            "--payload-format",
            "xacml",
        ],
    )

    assert result.exit_code == 0, result.output
    verify(mock_client).evaluate_raw(_raw_xacml())


def test_eval_payload_format_xacml_rejects_structured(tmp_path: Path) -> None:
    _stub_client()
    path = _write(tmp_path, "p.json", json.dumps(_structured_eval()))

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "pdp",
            "eval",
            "--payload",
            str(path),
            "--payload-format",
            "xacml",
        ],
    )

    assert result.exit_code != 0
    assert "Raw XACML" in result.output


def test_eval_still_works_with_flags_and_no_payload() -> None:
    mock_client = _stub_client()
    when(mock_client).evaluate(...).thenReturn(_permit_eval())

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "pdp",
            "eval",
            "--subject",
            "u1",
            "--resource",
            "doc1",
            "--resource-type",
            "file",
            "--action",
            "VIEW",
        ],
    )

    assert result.exit_code == 0, result.output


def test_eval_missing_required_flag_without_payload() -> None:
    _stub_client()
    result = runner.invoke(app, [*_GLOBAL_OPTS, "pdp", "eval", "--subject", "u1"])
    assert result.exit_code != 0


def test_permissions_payload_structured_json(tmp_path: Path) -> None:
    mock_client = _stub_client()
    when(mock_client).permissions(...).thenReturn(_permit_perm())
    path = _write(tmp_path, "p.json", json.dumps(_structured_perm()))

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "pdp", "permissions", "--payload", str(path)],
    )

    assert result.exit_code == 0, result.output
    verify(mock_client).permissions(ANY, content_type=ANY)


def test_permissions_payload_raw_xacml(tmp_path: Path) -> None:
    mock_client = _stub_client()
    when(mock_client).permissions_raw(...).thenReturn(_permit_perm())
    path = _write(tmp_path, "x.json", json.dumps(_raw_xacml()))

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "pdp", "permissions", "--payload", str(path)],
    )

    assert result.exit_code == 0, result.output
    verify(mock_client).permissions_raw(_raw_xacml())


def test_permissions_payload_conflicts_with_flags(tmp_path: Path) -> None:
    _stub_client()
    path = _write(tmp_path, "p.json", json.dumps(_structured_perm()))

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "pdp",
            "permissions",
            "--payload",
            str(path),
            "--resource",
            "r1",
        ],
    )

    assert result.exit_code != 0
    assert "--payload cannot be combined" in result.output
