"""CLI helper for bulk ``--id`` / ``--ids`` flag handling."""

from __future__ import annotations

import typer

from nextlabs_sdk._cli._output import print_error


def parse_bulk_ids(
    ids: list[int] | None,
    csv: str | None,
) -> list[int]:
    """Merge repeatable ``--id`` and CSV ``--ids`` inputs into a clean list.

    Args:
        ids: Repeated ``--id`` values already parsed by Typer as integers.
        csv: Raw CSV string from a single ``--ids`` option.

    Returns:
        A list of IDs with duplicates removed while preserving the order of
        first occurrence. Values from ``ids`` come before values from ``csv``.

    Raises:
        typer.Exit: With exit code ``1`` when the resulting list would be
            empty, when ``csv`` contains only separators/whitespace, or when
            any CSV element fails integer validation.
    """
    merged: list[int] = []
    seen: set[int] = set()

    _extend_unique(merged, seen, ids or ())
    if csv is not None:
        _extend_unique(merged, seen, _parse_csv(csv))

    if not merged:
        print_error("No IDs provided: pass --id (repeatable) or --ids CSV")
        raise typer.Exit(code=1)

    return merged


def _parse_csv(csv: str) -> list[int]:
    parsed_ids: list[int] = []
    for raw in csv.split(","):
        token = raw.strip()
        if token == "":
            continue
        try:
            parsed_ids.append(int(token))
        except ValueError:
            print_error(f"Invalid ID {token!r} in --ids (must be an integer)")
            raise typer.Exit(code=1) from None
    return parsed_ids


def _extend_unique(
    target: list[int],
    seen: set[int],
    source: "list[int] | tuple[int, ...]",
) -> None:
    for bulk_id in source:
        if bulk_id not in seen:
            seen.add(bulk_id)
            target.append(bulk_id)
