from __future__ import annotations

from pathlib import Path

import pytest
import typer

from nextlabs_sdk._cli._binary_output import write_bytes


def test_write_bytes_creates_new_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "out.bin"

    write_bytes(path, b"hello", overwrite=False)

    assert path.read_bytes() == b"hello"
    captured = capsys.readouterr().out.replace("\n", "")
    assert "5" in captured
    assert str(path) in captured


def test_write_bytes_refuses_to_overwrite_without_flag(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "out.bin"
    path.write_bytes(b"existing")

    with pytest.raises(typer.Exit) as exc:
        write_bytes(path, b"new", overwrite=False)

    assert exc.value.exit_code == 1
    assert path.read_bytes() == b"existing"
    assert "exists" in capsys.readouterr().out.lower()


def test_write_bytes_overwrites_with_flag(tmp_path: Path) -> None:
    path = tmp_path / "out.bin"
    path.write_bytes(b"existing")

    write_bytes(path, b"replaced", overwrite=True)

    assert path.read_bytes() == b"replaced"


def test_write_bytes_creates_parent_directory(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "deep" / "out.bin"

    write_bytes(path, b"data", overwrite=False)

    assert path.read_bytes() == b"data"


def test_write_bytes_handles_empty_bytes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "empty.bin"

    write_bytes(path, b"", overwrite=False)

    assert path.read_bytes() == b""
    assert "0" in capsys.readouterr().out
