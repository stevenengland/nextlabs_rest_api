"""CLI helper for writing binary responses to ``--output PATH`` targets."""

from __future__ import annotations

from pathlib import Path

import typer

from nextlabs_sdk._cli._output import print_error, print_success


def write_bytes(path: Path, payload: bytes, *, overwrite: bool) -> None:
    """Write raw bytes to ``path`` with an overwrite guard and success report.

    Args:
        path: Destination file path. Parent directories are created if missing.
        payload: Bytes to write.
        overwrite: When ``False`` (the default CLI behaviour), abort if
            ``path`` already exists. When ``True``, replace the existing file.

    Raises:
        typer.Exit: With exit code ``1`` when ``path`` exists and ``overwrite``
            is ``False``.
    """
    if path.exists() and not overwrite:
        print_error(f"File exists: {path} (pass --overwrite to replace)")
        raise typer.Exit(code=1)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    print_success(f"Wrote {len(payload)} bytes to {path}")
