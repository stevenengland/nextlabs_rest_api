"""Semantic Rich renderer for policy diff results."""

from __future__ import annotations

from rich.console import Console

from nextlabs_sdk._cli._diff._identity import ComponentSummary
from nextlabs_sdk._cli._diff._inline import highlight_inline
from nextlabs_sdk._cli._diff._models import DiffResult, FieldChange

_GLYPH_ADD = "[green]+[/green]"
_GLYPH_REMOVE = "[red]-[/red]"
_GLYPH_CHANGE = "[yellow]~[/yellow]"


def _format_component(summary: ComponentSummary | None) -> str:
    """Render a component summary as ``name (id=N)`` for display."""
    if summary is None:
        return "?"
    label = summary.name or "?"
    if summary.component_id is None:
        return label
    return f"{label} (id={summary.component_id})"


def _version_of(summary: ComponentSummary | None) -> int | None:
    if summary is None:
        return None
    return summary.version


def _format_version_bump(
    previous: ComponentSummary | None, summary: ComponentSummary | None
) -> str:
    return f"v{_version_of(previous)} \u2192 v{_version_of(summary)}"


def _render_component_change(con: Console, field: str, change: FieldChange) -> None:
    """Print a component-slot change identified by name and id."""
    summary = change.new if isinstance(change.new, ComponentSummary) else None
    previous = change.old if isinstance(change.old, ComponentSummary) else None
    if change.kind == "add":
        con.print(f"  {_GLYPH_ADD} {field}: {_format_component(summary)}")
    elif change.kind == "remove":
        con.print(f"  {_GLYPH_REMOVE} {field}: {_format_component(previous)}")
    else:
        bump = _format_version_bump(previous, summary)
        con.print(f"  {_GLYPH_CHANGE} {field}: {_format_component(summary)} {bump}")


def _render_scalar_change(con: Console, field: str, change: FieldChange) -> None:
    """Print a non-component FieldChange row to *con*."""
    if change.kind == "add":
        con.print(f"  {_GLYPH_ADD} {field}: {change.new}")
    elif change.kind == "remove":
        con.print(f"  {_GLYPH_REMOVE} {field}: {change.old}")
    elif isinstance(change.old, str) and isinstance(change.new, str):
        highlighted = highlight_inline(change.old, change.new)
        con.print(f"  {_GLYPH_CHANGE} {field}: {highlighted}")
    else:
        con.print(f"  {_GLYPH_CHANGE} {field}: {change.old!r} \u2192 {change.new!r}")


def _render_change(con: Console, field: str, change: FieldChange) -> None:
    """Print a single FieldChange row to *con*.

    Args:
        con: The Rich console to print to.
        field: Dot-joined path string for display.
        change: The field change to render.
    """
    if isinstance(change.old, ComponentSummary) or isinstance(
        change.new, ComponentSummary
    ):
        _render_component_change(con, field, change)
    else:
        _render_scalar_change(con, field, change)


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
