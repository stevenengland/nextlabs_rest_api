"""Unified git-style renderer for policy diff results."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from difflib import unified_diff

from rich.console import Console
from rich.markup import escape

from nextlabs_sdk._cli._diff._engine import canonicalise
from nextlabs_sdk._cli._diff._identity import COMPONENT_SLOT_FIELDS
from nextlabs_sdk._cli._diff._models import DiffHeader, DiffResult, FieldChange

_REVISION_LABEL = "revision"
_OPERATOR_FIELD = "operator"
_GROUPING_SEGMENT = "grouping"


@dataclass(frozen=True)
class UnifiedDiffInput:
    """Inputs for a unified render of one policy revision pair.

    Bundles the raw payloads (rendered as the JSON body), the identity header
    (labels), and the engine-computed delta (the source of grouping drift), so
    the renderer never recomputes the comparison it is handed.

    Attributes:
        old: The baseline alias-keyed policy payload.
        new: The revised alias-keyed policy payload.
        header: The policy identity and the compared revision numbers.
        diff_result: The structured delta already computed for this pair.
    """

    old: Mapping[str, object]
    new: Mapping[str, object]
    header: DiffHeader
    diff_result: DiffResult


def render_unified(
    diff: UnifiedDiffInput,
    *,
    show_all: bool = False,
    console: Console | None = None,
) -> None:
    """Render two revisions as a canonicalised git-style unified diff.

    Both revisions are canonicalised first (keys sorted on serialisation,
    arrays sorted by identity, noise stripped), so element re-ordering and
    deployment noise produce no diff lines. Raw component-slot group operators
    are dropped from the JSON body so cosmetic operator differences (case or
    whitespace) never produce a line; genuine operator/grouping drift is
    rendered as a structured block instead, keeping the unified output in
    parity with the semantic format and ``--exit-code``.

    Args:
        diff: The revision payloads, identity header, and engine-computed delta
            to render; grouping drift is read from ``diff.diff_result`` rather
            than recomputed, so the renderer shares one comparison source.
        show_all: When True, reveal ordering and noise differences and keep raw
            group operators in the body.
        console: Rich Console to print to; defaults to a new Console().
    """
    con = Console() if console is None else console
    header = diff.header
    con.print(f"Policy: {header.policy_name} (id={header.policy_id})")
    con.print()
    old_lines = _canonical_lines(diff.old, show_all=show_all)
    new_lines = _canonical_lines(diff.new, show_all=show_all)
    from_label = f"{_REVISION_LABEL} {header.from_rev}"
    to_label = f"{_REVISION_LABEL} {header.to_rev}"
    for line in unified_diff(
        old_lines,
        new_lines,
        fromfile=from_label,
        tofile=to_label,
        lineterm="",
    ):
        con.print(_colourise(line), highlight=False)
    if not show_all:
        for change in _grouping_changes(diff.diff_result):
            _render_grouping_change(con, change)


def _grouping_changes(diff_result: DiffResult) -> list[FieldChange]:
    return [
        change
        for change in diff_result.changes
        if change.path and change.path[-1] == _GROUPING_SEGMENT
    ]


def _canonical_lines(payload: Mapping[str, object], *, show_all: bool) -> list[str]:
    canonical = canonicalise(payload, show_all=show_all)
    if not show_all:
        canonical = _strip_slot_operators(canonical)
    return json.dumps(canonical, indent=2, sort_keys=True).splitlines()


def _strip_slot_operators(canonical: object) -> object:
    """Drop group ``operator`` keys from component slots in a canonical payload.

    Group operators are surfaced via the structured grouping block, so leaving
    them in the JSON body would double-report genuine flips and false-report
    cosmetic case/whitespace differences that the semantic format ignores.
    """
    if not isinstance(canonical, Mapping):
        return canonical
    stripped: dict[str, object] = {}
    for key, child in canonical.items():
        if key in COMPONENT_SLOT_FIELDS and isinstance(child, list):
            stripped[key] = [_strip_group_operator(group) for group in child]
        else:
            stripped[key] = child
    return stripped


def _strip_group_operator(group: object) -> object:
    if not isinstance(group, Mapping):
        return group
    return {key: member for key, member in group.items() if key != _OPERATOR_FIELD}


def _render_grouping_change(con: Console, change: FieldChange) -> None:
    path = ".".join(str(segment) for segment in change.path)
    _render_structure_lines(con, "-", path, change.old)
    _render_structure_lines(con, "+", path, change.new)


def _render_structure_lines(
    con: Console, glyph: str, path: str, structure: object
) -> None:
    lines = str(structure).split("\n")
    con.print(_colourise(f"{glyph}  {path}: {lines[0]}"))
    for line in lines[1:]:
        con.print(_colourise(f"{glyph}    {line}"))


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
