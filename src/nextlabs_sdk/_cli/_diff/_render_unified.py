"""Unified git-style renderer for policy diff results."""

from __future__ import annotations

import json
from collections.abc import Mapping
from difflib import unified_diff

from rich.console import Console
from rich.markup import escape

from nextlabs_sdk._cli._diff._engine import canonicalise


def render_unified(
    old: Mapping[str, object],
    new: Mapping[str, object],
    *,
    labels: tuple[str, str],
    show_all: bool = False,
    console: Console | None = None,
) -> None:
    """Render two revisions as a canonicalised git-style unified diff.

    Both revisions are canonicalised first (keys sorted on serialisation,
    arrays sorted by identity, noise stripped), so element re-ordering and
    deployment noise produce no diff lines.

    Args:
        old: The baseline alias-keyed policy payload.
        new: The revised alias-keyed policy payload.
        labels: The ``(from, to)`` labels for the diff header.
        show_all: When True, reveal ordering and noise differences.
        console: Rich Console to print to; defaults to a new Console().
    """
    con = Console() if console is None else console
    old_lines = _canonical_lines(old, show_all=show_all)
    new_lines = _canonical_lines(new, show_all=show_all)
    from_label, to_label = labels
    for line in unified_diff(
        old_lines,
        new_lines,
        fromfile=from_label,
        tofile=to_label,
        lineterm="",
    ):
        con.print(_colourise(line), highlight=False)


def _canonical_lines(payload: Mapping[str, object], *, show_all: bool) -> list[str]:
    canonical = canonicalise(payload, show_all=show_all)
    return json.dumps(canonical, indent=2, sort_keys=True).splitlines()


def _colourise(line: str) -> str:
    text = escape(line)
    if line.startswith(("---", "+++")):
        return f"[bold]{text}[/bold]"
    if line.startswith("@@"):
        return f"[cyan]{text}[/cyan]"
    if line.startswith("+"):
        return f"[green]{text}[/green]"
    if line.startswith("-"):
        return f"[red]{text}[/red]"
    return text
