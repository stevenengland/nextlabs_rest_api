"""Unified git-style renderer for policy diff results."""

from __future__ import annotations

import json
from collections.abc import Mapping
from difflib import unified_diff

from rich.console import Console
from rich.markup import escape

from nextlabs_sdk._cli._diff._engine import canonicalise, diff_payloads
from nextlabs_sdk._cli._diff._identity import COMPONENT_SLOT_FIELDS
from nextlabs_sdk._cli._diff._models import DiffHeader, FieldChange

_REVISION_LABEL = "revision"
_OPERATOR_FIELD = "operator"
_GROUPING_SEGMENT = "grouping"


def render_unified(
    old: Mapping[str, object],
    new: Mapping[str, object],
    header: DiffHeader,
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
        old: The baseline alias-keyed policy payload.
        new: The revised alias-keyed policy payload.
        header: The policy identity and compared revisions; the policy row is
            printed first and the ``--- / +++`` labels derive from its revision
            numbers.
        show_all: When True, reveal ordering and noise differences and keep raw
            group operators in the body.
        console: Rich Console to print to; defaults to a new Console().
    """
    con = Console() if console is None else console
    con.print(f"Policy: {header.policy_name} (id={header.policy_id})")
    con.print()
    old_lines = _canonical_lines(old, show_all=show_all)
    new_lines = _canonical_lines(new, show_all=show_all)
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
        for change in _grouping_changes(old, new):
            _render_grouping_change(con, change)


def _grouping_changes(
    old: Mapping[str, object], new: Mapping[str, object]
) -> list[FieldChange]:
    return [
        change
        for change in diff_payloads(old, new).changes
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
