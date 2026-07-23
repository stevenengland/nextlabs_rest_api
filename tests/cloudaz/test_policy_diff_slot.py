from __future__ import annotations

from typing import Any

from nextlabs_sdk._cli._diff._models import FieldChange
from nextlabs_sdk._cli._diff._slot import compare_slot


def _comp(component_id: int | None, name: str, version: int = 1) -> dict[str, Any]:
    return {
        "id": component_id,
        "name": name,
        "version": version,
        "subComponents": [],
    }


def _group(operator: str, *components: dict[str, Any]) -> dict[str, Any]:
    return {"operator": operator, "components": list(components)}


def _grouping_change(changes: list[FieldChange]) -> FieldChange | None:
    for change in changes:
        if change.path == ("grouping",):
            return change
    return None


def _membership_changes(changes: list[FieldChange]) -> list[FieldChange]:
    return [change for change in changes if change.path == ()]


_A = _comp(1, "A")
_B = _comp(2, "B")
_C = _comp(3, "C")


def test_operator_flip_with_identical_members_yields_grouping_change() -> None:
    """Given two slots holding the same members under a flipped group operator.

    When comparing the slots.
    Then a grouping change is emitted and no per-component change is.
    """
    old_slot = [_group("OR", _A, _B)]
    new_slot = [_group("AND", _A, _B)]

    changes = compare_slot(old_slot, new_slot)

    grouping = _grouping_change(changes)
    assert grouping is not None
    assert grouping.kind == "change"
    assert _membership_changes(changes) == []


def test_operator_flip_render_uses_canonical_structure_strings() -> None:
    """Given a slot whose first group operator flips with a stable second group.

    When comparing the slots.
    Then the grouping change carries the exact multi-line structure strings,
    members sorted by identity and continuation groups prefixed with ``AND``.
    """
    old_slot = [_group("OR", _A, _B), _group("AND", _C)]
    new_slot = [_group("AND", _B, _A), _group("AND", _C)]

    grouping = _grouping_change(compare_slot(old_slot, new_slot))

    assert grouping is not None
    assert grouping.old == "[OR : A, B]\nAND [AND: C]"
    assert grouping.new == "[AND: A, B]\nAND [AND: C]"


def test_in_place_version_change_stays_per_component_without_grouping() -> None:
    """Given a slot whose only difference is a component version bump.

    When comparing the slots.
    Then a single per-component change is emitted and no grouping change is.
    """
    old_slot = [_group("AND", _comp(1, "A", version=1))]
    new_slot = [_group("AND", _comp(1, "A", version=2))]

    changes = compare_slot(old_slot, new_slot)

    assert _grouping_change(changes) is None
    membership = _membership_changes(changes)
    assert len(membership) == 1
    assert membership[0].kind == "change"


def test_pure_add_and_remove_stays_per_component_without_grouping() -> None:
    """Given a slot where one component is replaced by another.

    When comparing the slots.
    Then per-component add and remove are emitted and no grouping change is.
    """
    old_slot = [_group("AND", _A)]
    new_slot = [_group("AND", _B)]

    changes = compare_slot(old_slot, new_slot)

    assert _grouping_change(changes) is None
    kinds = sorted(change.kind for change in _membership_changes(changes))
    assert kinds == ["add", "remove"]


def test_combined_add_remove_and_operator_flip() -> None:
    """Given a slot where a member is replaced and the group operator flips.

    When comparing the slots.
    Then both per-component add/remove and a grouping change are emitted, and
    the grouping change is scoped to the members present in both revisions.
    """
    old_slot = [_group("OR", _A, _C)]
    new_slot = [_group("AND", _B, _C)]

    changes = compare_slot(old_slot, new_slot)

    grouping = _grouping_change(changes)
    assert grouping is not None
    assert grouping.old == "[OR : C]"
    assert grouping.new == "[AND: C]"
    kinds = sorted(change.kind for change in _membership_changes(changes))
    assert kinds == ["add", "remove"]


def test_cross_group_move_surfaces_as_grouping_not_add_remove() -> None:
    """Given a component moved between operator groups with stable membership.

    When comparing the slots.
    Then the move surfaces as a grouping change, never as removed plus added.
    """
    old_slot = [_group("OR", _A, _B), _group("AND", _C)]
    new_slot = [_group("OR", _A, _C), _group("AND", _B)]

    changes = compare_slot(old_slot, new_slot)

    assert _grouping_change(changes) is not None
    assert _membership_changes(changes) == []


def test_operator_case_and_whitespace_differences_are_ignored() -> None:
    """Given two slots that differ only in operator casing and whitespace.

    When comparing the slots.
    Then no grouping change is emitted.
    """
    old_slot = [_group("AND", _A, _B)]
    new_slot = [_group(" and ", _A, _B)]

    assert _grouping_change(compare_slot(old_slot, new_slot)) is None


def test_idless_components_render_by_name() -> None:
    """Given grouped components that carry no id.

    When comparing slots whose group operator flips.
    Then members render by their name in the structure strings.
    """
    old_slot = [_group("OR", _comp(None, "Zebra"), _comp(None, "Ant"))]
    new_slot = [_group("AND", _comp(None, "Ant"), _comp(None, "Zebra"))]

    grouping = _grouping_change(compare_slot(old_slot, new_slot))

    assert grouping is not None
    assert grouping.old == "[OR : Ant, Zebra]"
    assert grouping.new == "[AND: Ant, Zebra]"
