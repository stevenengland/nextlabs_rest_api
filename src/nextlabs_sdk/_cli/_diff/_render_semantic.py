"""Semantic Rich renderer for policy diff results."""

from __future__ import annotations

from rich.console import Console

from nextlabs_sdk._cli._diff._identity import (
    ComponentSummary,
    ObligationSummary,
    TagSummary,
)
from nextlabs_sdk._cli._diff._inline import highlight_pair
from nextlabs_sdk._cli._diff._models import (
    CountMarker,
    DiffHeader,
    DiffResult,
    FieldChange,
)

_GLYPH_ADD = "[green]+[/green]"
_GLYPH_REMOVE = "[red]-[/red]"
_GLYPH_CHANGE = "[yellow]~[/yellow]"
_KIND_ADD = "add"
_UNKNOWN = "?"
_POLICY_LABEL = "Policy:"
_ARROW = "\u2192"
_GROUPING_SEGMENT = "grouping"
_CONTINUATION_PREFIX = "AND "
_IDENTITY_NOTE = "identity fields ignored"


def _render_header(con: Console, header: DiffHeader, *, show_all: bool) -> None:
    """Print the identity header for a single- or cross-policy diff."""
    if header.is_cross_policy:
        con.print(
            f"[bold]A:[/bold] {header.policy_name} (id={header.policy_id}) "
            f"revision {header.from_rev}"
        )
        con.print(
            f"[bold]B:[/bold] {header.to_policy_name} (id={header.to_policy_id}) "
            f"revision {header.to_rev}"
        )
        if not show_all:
            con.print(f"[dim]{_IDENTITY_NOTE}[/dim]")
    else:
        con.print(
            f"[bold]{_POLICY_LABEL}[/bold] {header.policy_name} "
            f"(id={header.policy_id})"
        )
        con.print(f"Comparing revisions {header.from_rev} {_ARROW} {header.to_rev}")


def _format_component(summary: ComponentSummary | None) -> str:
    """Render a component summary as ``name (id=N)`` for display."""
    if summary is None:
        return _UNKNOWN
    label = summary.name or _UNKNOWN
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
    if change.kind == _KIND_ADD:
        con.print(f"  {_GLYPH_ADD} {field}: {_format_component(summary)}")
    elif change.kind == "remove":
        con.print(f"  {_GLYPH_REMOVE} {field}: {_format_component(previous)}")
    else:
        bump = _format_version_bump(previous, summary)
        con.print(f"  {_GLYPH_CHANGE} {field}: {_format_component(summary)} {bump}")


def _scalar_display(raw: object) -> str:
    """Return the display string for a scalar value, with placeholders for empty/None."""
    if raw is None:
        return "[dim](none)[/dim]"
    if raw == "":
        return "[dim](empty)[/dim]"
    return str(raw)


def _render_scalar_change_lines(con: Console, field: str, change: FieldChange) -> None:
    """Print the two-line header + old/new body for an in-place scalar change."""
    con.print(f"  {_GLYPH_CHANGE} {field}:")
    if isinstance(change.old, str) and isinstance(change.new, str):
        old_markup, new_markup = highlight_pair(change.old, change.new)
        old_display = "[dim](empty)[/dim]" if change.old == "" else old_markup
        new_display = "[dim](empty)[/dim]" if change.new == "" else new_markup
    else:
        old_display = _scalar_display(change.old)
        new_display = _scalar_display(change.new)
    con.print(f"    {_GLYPH_REMOVE} {old_display}")
    con.print(f"    {_GLYPH_ADD} {new_display}")


def _render_scalar_change(con: Console, field: str, change: FieldChange) -> None:
    """Print a non-component FieldChange row to *con*."""
    if change.kind == _KIND_ADD:
        con.print(f"  {_GLYPH_ADD} {field}: {change.new}")
    elif change.kind == "remove":
        con.print(f"  {_GLYPH_REMOVE} {field}: {change.old}")
    else:
        _render_scalar_change_lines(con, field, change)


def _render_obligation_change(con: Console, field: str, change: FieldChange) -> None:
    """Print an added or removed obligation identified by name."""
    summary = change.new if isinstance(change.new, ObligationSummary) else change.old
    label = summary.name if isinstance(summary, ObligationSummary) else _UNKNOWN
    if change.kind == _KIND_ADD:
        con.print(f"  {_GLYPH_ADD} {field}: {label}")
    else:
        con.print(f"  {_GLYPH_REMOVE} {field}: {label}")


def _format_tag(summary: TagSummary) -> str:
    key = summary.key or _UNKNOWN
    label = summary.label or _UNKNOWN
    return f"{key} ({label})"


def _render_tag_change(con: Console, change: FieldChange) -> None:
    """Print an added or removed tag as 'key (LABEL)' glyph line."""
    summary = change.new if isinstance(change.new, TagSummary) else change.old
    display = _format_tag(summary) if isinstance(summary, TagSummary) else _UNKNOWN
    if change.kind == _KIND_ADD:
        con.print(f"  {_GLYPH_ADD} {display}")
    else:
        con.print(f"  {_GLYPH_REMOVE} {display}")


def _render_grouping_change(con: Console, change: FieldChange) -> None:
    """Print a slot grouping change as aligned ``was``/``now`` structure blocks.

    The first group of each revision prints inline after its label; each
    continuation group (already carrying the implicit ``AND`` prefix) prints on
    its own line, indented so every group's opening bracket aligns.
    """
    con.print(f"  {_GLYPH_CHANGE} {_GROUPING_SEGMENT}:")
    _render_structure_block(con, "was", change.old)
    _render_structure_block(con, "now", change.new)


def _render_structure_block(con: Console, label: str, structure: object) -> None:
    lines = str(structure).split("\n")
    con.print(f"      {label}:  {lines[0]}")
    for line in lines[1:]:
        con.print(f"        {line}")


def _render_change(con: Console, field: str, change: FieldChange) -> None:
    """Print a single FieldChange row to *con*.

    Args:
        con: The Rich console to print to.
        field: Dot-joined path string for display.
        change: The field change to render.
    """
    if change.path and change.path[-1] == _GROUPING_SEGMENT:
        _render_grouping_change(con, change)
    else:
        _render_typed_change(con, field, change)


def _render_typed_change(con: Console, field: str, change: FieldChange) -> None:
    if isinstance(change.old, ObligationSummary) or isinstance(
        change.new, ObligationSummary
    ):
        _render_obligation_change(con, field, change)
    elif isinstance(change.old, TagSummary) or isinstance(change.new, TagSummary):
        _render_tag_change(con, change)
    elif isinstance(change.old, ComponentSummary) or isinstance(
        change.new, ComponentSummary
    ):
        _render_component_change(con, field, change)
    else:
        _render_scalar_change(con, field, change)


def _markers_by_section(markers: tuple[CountMarker, ...]) -> dict[str, CountMarker]:
    """Index single-segment count markers by their field name for header lookup."""
    indexed: dict[str, CountMarker] = {}
    for marker in markers:
        if len(marker.path) == 1:
            indexed[marker.path[0]] = marker
    return indexed


def _count_suffix(marker: CountMarker | None) -> str:
    """Render the ``[old → new]`` header suffix for a changed-count field."""
    if marker is None:
        return ""
    return f" \\[{marker.old_count} {_ARROW} {marker.new_count}]"


def render_semantic(
    diff: DiffResult,
    header: DiffHeader,
    *,
    show_all: bool = False,
    console: Console | None = None,
) -> None:
    """Render a DiffResult as a Rich semantic report.

    In-place scalar edits show only the changed words highlighted.
    A footer is printed when noise-only changes were filtered.

    Args:
        diff: The structured diff result to render.
        header: The policy identity and compared revisions, printed as two
            lines above the change sections.
        show_all: When True, identity fields are revealed in cross-policy mode,
            so the "identity fields ignored" header note is suppressed.
        console: Rich Console to print to; defaults to a new Console().
    """
    con = Console() if console is None else console
    _render_header(con, header, show_all=show_all)
    con.print()

    sections: dict[str, list[FieldChange]] = {}
    for change in diff.changes:
        sections.setdefault(change.path[0], []).append(change)

    markers = _markers_by_section(diff.count_markers)
    for section, changes in sections.items():
        con.print(f"\n[bold]{section}[/bold]{_count_suffix(markers.get(section))}")
        for change in changes:
            field = ".".join(str(segment) for segment in change.path)
            _render_change(con, field, change)

    if diff.hidden_noise_count > 0:
        con.print(f"\n[dim]{diff.hidden_noise_count} noise-only change(s) hidden[/dim]")
