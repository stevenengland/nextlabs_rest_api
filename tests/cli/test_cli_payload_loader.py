from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer

from nextlabs_sdk._cli._payload_loader import load_payload


def test_load_payload_reads_valid_json_object(tmp_path: Path) -> None:
    path = tmp_path / "payload.json"
    path.write_text(json.dumps({"name": "Policy A", "effectType": "ALLOW"}))

    assert load_payload(path) == {"name": "Policy A", "effectType": "ALLOW"}


def test_load_payload_errors_on_missing_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(typer.Exit) as exc:
        load_payload(tmp_path / "does_not_exist.json")
    assert exc.value.exit_code == 1
    assert "not found" in capsys.readouterr().out.lower()


def test_load_payload_errors_on_invalid_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json")

    with pytest.raises(typer.Exit) as exc:
        load_payload(path)
    assert exc.value.exit_code == 1
    assert "invalid json" in capsys.readouterr().out.lower()


def test_load_payload_errors_on_non_object_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "array.json"
    path.write_text("[1, 2, 3]")

    with pytest.raises(typer.Exit) as exc:
        load_payload(path)
    assert exc.value.exit_code == 1
    assert "object" in capsys.readouterr().out.lower()


def test_load_payload_errors_on_directory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(typer.Exit) as exc:
        load_payload(tmp_path)
    assert exc.value.exit_code == 1
    output = capsys.readouterr().out.lower()
    assert "not found" in output or "read" in output
