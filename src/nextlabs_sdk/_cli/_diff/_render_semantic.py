"""Semantic Rich renderer for policy diff results."""

from __future__ import annotations

from rich.console import Console

from nextlabs_sdk._cli._diff._inline import highlight_inline
from nextlabs_sdk._cli._diff._models import DiffResult, FieldChange

_GLYPH_ADD = "[green]+[/green]"
_GLYPH_REMOVE = "[red]-[/red]"
_GLYPH_CHANGE = "[yellow]~[/yellow]"


def _render_change(con: Console, field: str, change: FieldChange) -> None:
    """Print a single FieldChange row to *con*.

    Args:
        con: The Rich console to print to.
        field: Dot-joined path string for display.
        change: The field change to render.
    """
    if change.kind == "add":
        con.print(f"  {_GLYPH_ADD} {field}: {change.new}")
    elif change.kind == "remove":
        con.print(f"  {_GLYPH_REMOVE} {field}: {change.old}")
    elif isinstance(change.old, str) and isinstance(change.new, str):
        highlighted = highlight_inline(change.old, change.new)
        con.print(f"  {_GLYPH_CHANGE} {field}: {highlighted}")
    else:
        con.print(f"  {_GLYPH_CHANGE} {field}: {change.old!r} \u2192 {change.new!r}")


def render_semantic(diff: DiffResult, *, console: Console | None = None) -> None:
    """Render a DiffResult as a Rich semantic report.

    In-place scalar edits show only the changed words highlighted.
    A footer is printed when noise-only changes were filtered.

    Args:
        diff: The structured diff result to render.
        console: Rich Console to print to; defaults to a new Console().
    """
    con = Console() if console is None else console
    con.print("[bold]Policy diff[/bold]")

    sections: dict[str, list[FieldChange]] = {}
    for change in diff.changes:
        sections.setdefault(change.path[0], []).append(change)

    for section, changes in sections.items():
        con.print(f"\n[bold]{section}[/bold]")
        for change in changes:
            field = ".".join(str(segment) for segment in change.path)
            _render_change(con, field, change)

    if diff.hidden_noise_count > 0:
        con.print(f"\n[dim]{diff.hidden_noise_count} noise-only change(s) hidden[/dim]")
