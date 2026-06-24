"""Operator/grouping-aware comparison for a single policy component slot.

This module is the slot-comparison seam: the diff engine delegates per-slot
comparison here instead of flattening every group into one identity set. The
comparison has two parts over the same slot pair — order-free **membership**
(today's per-component behaviour, preserved) and **grouping**, which surfaces a
single change when the ``(operator, members)`` partition drifts over the
components present in both revisions. Group structure is a plain
``(operator, frozenset[identity])`` tuple; no new class is introduced.
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from typing import Literal, TypeAlias

from nextlabs_sdk._cli._diff._identity import (
    ComponentSummary,
    flatten_slot,
    identity_key,
)
from nextlabs_sdk._cli._diff._models import FieldChange

_KIND_ADD: Literal["add"] = "add"
_KIND_REMOVE: Literal["remove"] = "remove"
_KIND_CHANGE: Literal["change"] = "change"

_GROUPING_SEGMENT = "grouping"
_SCHEMA_TYPE = "ComponentDTORes"
_OPERATOR_FIELD = "operator"
_COMPONENTS_FIELD = "components"
_SUBCOMPONENTS_FIELD = "subComponents"
_OPERATOR_WIDTH = 3
_UNKNOWN_MEMBER = "?"

_Group: TypeAlias = "tuple[str, frozenset[Hashable]]"
_Summaries: TypeAlias = "Mapping[Hashable, ComponentSummary]"


def compare_slot(old_slot: object, new_slot: object) -> list[FieldChange]:
    """Compare two component-slot values for membership and grouping drift.

    Membership changes are order-free and identity-keyed (id, falling back to
    name) — a component that merely moves position or moves between groups is
    still recognised as present. A grouping change is emitted when the
    ``(normalised-operator, members)`` partition of the components present in
    both revisions differs; it reuses ``kind="change"`` with a ``grouping``
    path suffix and carries the canonical structure strings.

    Args:
        old_slot: The baseline alias-keyed slot value (a list of groups).
        new_slot: The revised alias-keyed slot value (a list of groups).

    Returns:
        A list of relative :class:`FieldChange` records — membership changes
        carry an empty path, the grouping change carries ``("grouping",)`` —
        for the engine to prefix with the slot name.
    """
    old_components = flatten_slot(old_slot)
    new_components = flatten_slot(new_slot)

    changes: list[FieldChange] = []
    for key in old_components.keys() | new_components.keys():
        change = _classify_component(old_components.get(key), new_components.get(key))
        if change is not None:
            changes.append(change)

    grouping = _grouping_change(old_slot, new_slot, old_components, new_components)
    if grouping is not None:
        changes.append(grouping)
    return changes


def _classify_component(
    old_summary: ComponentSummary | None,
    new_summary: ComponentSummary | None,
) -> FieldChange | None:
    if old_summary is not None and new_summary is not None:
        if old_summary == new_summary:
            return None
        return FieldChange(path=(), kind=_KIND_CHANGE, old=old_summary, new=new_summary)
    if new_summary is not None:
        return FieldChange(path=(), kind=_KIND_ADD, old=None, new=new_summary)
    return FieldChange(path=(), kind=_KIND_REMOVE, old=old_summary, new=None)


def _grouping_change(
    old_slot: object,
    new_slot: object,
    old_components: _Summaries,
    new_components: _Summaries,
) -> FieldChange | None:
    shared = old_components.keys() & new_components.keys()
    if not shared:
        return None

    old_groups = _partition(old_slot, frozenset(shared))
    new_groups = _partition(new_slot, frozenset(shared))
    if _normalised(old_groups) == _normalised(new_groups):
        return None

    summaries = {**old_components, **new_components}
    return FieldChange(
        path=(_GROUPING_SEGMENT,),
        kind=_KIND_CHANGE,
        old=_render_structure(old_groups, summaries),
        new=_render_structure(new_groups, summaries),
    )


def _partition(slot_value: object, shared: frozenset[Hashable]) -> list[_Group]:
    groups: list[_Group] = []
    for group in _mappings(slot_value):
        operator = group.get(_OPERATOR_FIELD)
        operator_str = operator if isinstance(operator, str) else ""
        members = frozenset(key for key in _group_identities(group) if key in shared)
        if members:
            groups.append((operator_str, members))
    return groups


def _normalised(groups: list[_Group]) -> frozenset[_Group]:
    return frozenset(
        (operator.casefold().strip(), members) for operator, members in groups
    )


def _group_identities(group: Mapping[str, object]) -> set[Hashable]:
    keys: set[Hashable] = set()
    for component in _mappings(group.get(_COMPONENTS_FIELD)):
        _collect_identities(component, keys)
    return keys


def _collect_identities(component: Mapping[str, object], keys: set[Hashable]) -> None:
    key = identity_key(_SCHEMA_TYPE, component)
    if key is not None:
        keys.add(key)
    for sub in _mappings(component.get(_SUBCOMPONENTS_FIELD)):
        _collect_identities(sub, keys)


def _render_structure(groups: list[_Group], summaries: _Summaries) -> str:
    lines: list[str] = []
    for index, (operator, members) in enumerate(sorted(groups, key=_group_sort_key)):
        rendered = _render_group(operator, members, summaries)
        lines.append(rendered if index == 0 else f"AND {rendered}")
    return "\n".join(lines)


def _render_group(
    operator: str, members: frozenset[Hashable], summaries: _Summaries
) -> str:
    labels = [
        _member_label(key, summaries) for key in sorted(members, key=_identity_sort_key)
    ]
    return f"[{operator.ljust(_OPERATOR_WIDTH)}: {', '.join(labels)}]"


def _member_label(key: Hashable, summaries: _Summaries) -> str:
    summary = summaries.get(key)
    if summary is None:
        return _UNKNOWN_MEMBER
    if summary.name:
        return summary.name
    if summary.component_id is not None:
        return f"id={summary.component_id}"
    return _UNKNOWN_MEMBER


def _group_sort_key(group: _Group) -> tuple[list[str], str]:
    operator, members = group
    return (sorted(_identity_sort_key(key) for key in members), operator.casefold())


def _identity_sort_key(key: Hashable) -> str:
    return str(key)


def _mappings(value: object) -> list[Mapping[str, object]]:  # noqa: WPS110
    if not isinstance(value, list):
        return []
    return [element for element in value if isinstance(element, Mapping)]
