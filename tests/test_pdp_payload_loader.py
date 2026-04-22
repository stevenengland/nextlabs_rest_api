"""Tests for the public PDP payload loader (structured JSON/YAML + raw XACML)."""

from __future__ import annotations

import builtins
import json
from pathlib import Path
from typing import Any

import pytest

from nextlabs_sdk.exceptions import PdpPayloadError
from nextlabs_sdk.pdp import (
    EvalRequest,
    PermissionsRequest,
)
from nextlabs_sdk.pdp.payloads import (
    LoadedPayload,
    PayloadFormat,
    load_eval_payload,
    load_permissions_payload,
)


def _structured_eval() -> dict[str, Any]:
    return {
        "subject": {"id": "user@example.com"},
        "action": {"id": "VIEW"},
        "resource": {"id": "doc:1", "type": "documents"},
        "application": {"id": "my-app"},
    }


def _structured_permissions() -> dict[str, Any]:
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
                    "CategoryId": "urn:oasis:names:tc:xacml:3.0:attribute-category:access-subject",
                    "Attribute": [
                        {
                            "AttributeId": "urn:oasis:names:tc:xacml:1.0:subject:subject-id",
                            "Value": "user@example.com",
                        },
                    ],
                },
            ],
        },
    }


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_load_eval_structured_json_from_path(tmp_path: Path) -> None:
    path = _write(tmp_path, "eval.json", json.dumps(_structured_eval()))
    loaded = load_eval_payload(path)
    assert loaded.kind == "structured"
    assert isinstance(loaded.request, EvalRequest)
    assert loaded.request.subject.id == "user@example.com"


def test_load_permissions_structured_json_from_path(tmp_path: Path) -> None:
    path = _write(tmp_path, "perm.json", json.dumps(_structured_permissions()))
    loaded = load_permissions_payload(path)
    assert loaded.kind == "structured"
    assert isinstance(loaded.request, PermissionsRequest)


def test_load_eval_structured_yaml_auto_detect(tmp_path: Path) -> None:
    yaml_text = (
        "subject:\n  id: user@example.com\n"
        "action:\n  id: VIEW\n"
        "resource:\n  id: doc:1\n  type: documents\n"
        "application:\n  id: my-app\n"
    )
    path = _write(tmp_path, "eval.yaml", yaml_text)
    loaded = load_eval_payload(path)
    assert loaded.kind == "structured"
    assert isinstance(loaded.request, EvalRequest)
    assert loaded.request.action.id == "VIEW"


def test_load_raw_xacml_auto_detect(tmp_path: Path) -> None:
    path = _write(tmp_path, "xacml.json", json.dumps(_raw_xacml()))
    loaded = load_eval_payload(path)
    assert loaded.kind == "raw_xacml"
    assert loaded.body == _raw_xacml()


def test_load_force_xacml_rejects_structured(tmp_path: Path) -> None:
    path = _write(tmp_path, "struct.json", json.dumps(_structured_eval()))
    with pytest.raises(PdpPayloadError, match="Raw XACML payload missing"):
        load_eval_payload(path, payload_format=PayloadFormat.XACML_JSON)


def test_load_force_json_on_yaml_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, "bad.yaml", "subject:\n  id: x\n")
    with pytest.raises(PdpPayloadError, match="Invalid JSON"):
        load_eval_payload(path, payload_format=PayloadFormat.JSON)


def test_load_force_yaml_on_json_ok(tmp_path: Path) -> None:
    path = _write(tmp_path, "ambiguous", json.dumps(_structured_eval()))
    loaded = load_eval_payload(path, payload_format=PayloadFormat.YAML)
    assert loaded.kind == "structured"


def test_load_missing_file(tmp_path: Path) -> None:
    with pytest.raises(PdpPayloadError, match="Payload file not found"):
        load_eval_payload(tmp_path / "nope.json")


def test_load_empty_file(tmp_path: Path) -> None:
    path = _write(tmp_path, "empty.json", "")
    with pytest.raises(PdpPayloadError, match="Empty JSON payload"):
        load_eval_payload(path)


def test_load_non_object_root(tmp_path: Path) -> None:
    path = _write(tmp_path, "list.json", "[1, 2, 3]")
    with pytest.raises(PdpPayloadError, match="root must be an object"):
        load_eval_payload(path)


def test_load_invalid_structured_surfaces_field_path(tmp_path: Path) -> None:
    path = _write(tmp_path, "broken.json", json.dumps({"subject": "not-an-object"}))
    with pytest.raises(PdpPayloadError, match="Invalid structured payload.*subject"):
        load_eval_payload(path)


def test_load_from_string_source() -> None:
    loaded = load_eval_payload(json.dumps(_structured_eval()))
    assert loaded.kind == "structured"


def test_load_from_bytes_source() -> None:
    loaded = load_eval_payload(json.dumps(_structured_eval()).encode("utf-8"))
    assert loaded.kind == "structured"


def test_load_from_invalid_bytes_source() -> None:
    with pytest.raises(PdpPayloadError, match="not valid UTF-8"):
        load_eval_payload(b"\xff\xfe\x00")


def test_load_raw_xacml_force_accepts_xacml(tmp_path: Path) -> None:
    path = _write(tmp_path, "x.json", json.dumps(_raw_xacml()))
    loaded = load_eval_payload(path, payload_format=PayloadFormat.XACML_JSON)
    assert loaded.kind == "raw_xacml"


def test_load_yaml_missing_pyyaml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = _write(tmp_path, "x.yaml", "a: 1\n")
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "yaml":
            raise ImportError("No module named 'yaml'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(PdpPayloadError, match="YAML support requires PyYAML"):
        load_eval_payload(path, payload_format=PayloadFormat.YAML)


def test_loaded_payload_structured_factory() -> None:
    req = EvalRequest.model_validate(_structured_eval())
    loaded = LoadedPayload.structured(req)
    assert loaded.kind == "structured"
    assert loaded.request is req
    assert loaded.body is None


def test_loaded_payload_raw_xacml_factory() -> None:
    loaded = LoadedPayload.raw_xacml(_raw_xacml())
    assert loaded.kind == "raw_xacml"
    assert loaded.body == _raw_xacml()
    assert loaded.request is None


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, "broken.yaml", "key: [unclosed\n")
    with pytest.raises(PdpPayloadError, match="Invalid YAML"):
        load_eval_payload(path, payload_format=PayloadFormat.YAML)


def test_yaml_non_object_root(tmp_path: Path) -> None:
    path = _write(tmp_path, "list.yaml", "- 1\n- 2\n")
    with pytest.raises(PdpPayloadError, match="YAML payload root must be an object"):
        load_eval_payload(path, payload_format=PayloadFormat.YAML)


def test_xacml_force_missing_category_list(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "bad.json",
        json.dumps({"Request": {"Category": "oops"}}),
    )
    with pytest.raises(PdpPayloadError, match="'Request.Category' must be a list"):
        load_eval_payload(path, payload_format=PayloadFormat.XACML_JSON)
