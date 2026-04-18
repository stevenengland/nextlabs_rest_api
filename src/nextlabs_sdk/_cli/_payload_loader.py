"""CLI helper for loading JSON request bodies from files."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from nextlabs_sdk._cli._output import print_error


def load_payload(path: Path) -> dict[str, object]:
    """Read and parse a JSON payload file for an API request body.

    Args:
        path: Filesystem path to a JSON file containing a single object.

    Returns:
        The parsed JSON object as a ``dict``.

    Raises:
        typer.Exit: With exit code ``1`` when the file is missing, cannot be
            read, contains invalid JSON, or its root value is not an object.
    """
    raw_text = _read_payload_file(path)
    parsed = _decode_json(path, raw_text)
    if not isinstance(parsed, dict):
        print_error(f"Payload in {path} must be a JSON object")
        raise typer.Exit(code=1)
    return parsed


def _read_payload_file(path: Path) -> str:
    if not path.is_file():
        print_error(f"Payload file not found: {path}")
        raise typer.Exit(code=1)
    try:
        return path.read_text()
    except OSError as exc:
        print_error(f"Could not read payload file {path}: {exc}")
        raise typer.Exit(code=1) from None


def _decode_json(path: Path, raw_text: str) -> object:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print_error(f"Invalid JSON in payload file {path}: {exc.msg}")
        raise typer.Exit(code=1) from None


def reject_data_flag(legacy_data: str | None) -> None:
    """Emit a migration error when the deprecated ``--data`` flag is used.

    Args:
        legacy_data: The value captured from a hidden ``--data`` typer option.

    Raises:
        typer.Exit: With exit code ``1`` when ``legacy_data`` is not ``None``.
    """
    if legacy_data is not None:
        print_error(
            "--data is no longer supported; use --payload PATH "
            "to load a JSON file instead.",
        )
        raise typer.Exit(code=1)


def require_payload(payload_path: Path | None) -> dict[str, object]:
    """Load the payload at ``payload_path`` or abort when the flag is missing.

    Args:
        payload_path: Value of the ``--payload`` typer option.

    Returns:
        The parsed JSON object.

    Raises:
        typer.Exit: With exit code ``1`` when ``payload_path`` is ``None``.
    """
    if payload_path is None:
        print_error("Missing required option: --payload PATH")
        raise typer.Exit(code=1)
    return load_payload(payload_path)
