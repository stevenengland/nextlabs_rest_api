from __future__ import annotations

from typing import Any

import pytest

from nextlabs_sdk._cli._diff._engine import diff_payloads
from nextlabs_sdk._cli._diff._identity import (
    COMPONENT_SLOT_FIELDS,
    ComponentSummary,
    flatten_slot,
    identity_key,
)


def _comp(
    component_id: int | None,
    name: str,
    version: int = 1,
    subs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": component_id,
        "name": name,
        "version": version,
        "subComponents": subs or [],
    }


def _slot(*components: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"operator": "AND", "components": list(components)}]


def _slot_changes(result: Any, field: str) -> list[Any]:
    return [
        change for change in result.changes if change.path and change.path[0] == field
    ]


def test_identity_key_uses_id_when_present():
    """Given a component dict carrying an id.

    When resolving its identity key for the ComponentDTORes schema type.
    Then the key is derived from the id.
    """
    key = identity_key("ComponentDTORes", {"id": 5, "name": "Engineers"})

    assert key == identity_key("ComponentDTORes", {"id": 5, "name": "Renamed"})


def test_identity_key_falls_back_to_name_when_id_absent():
    """Given a component dict with no id but a name.

    When resolving its identity key.
    Then the key is derived from the name.
    """
    key = identity_key("ComponentDTORes", {"id": None, "name": "Engineers"})

    assert key is not None
    assert key == identity_key("ComponentDTORes", {"name": "Engineers"})
    assert key != identity_key("ComponentDTORes", {"name": "Other"})


def test_flatten_slot_recurses_subcomponents_by_id():
    """Given a slot whose component nests another component via subComponents.

    When flattening the slot.
    Then both the parent and the nested component are collected by id.
    """
    slot = _slot(_comp(5, "Group", subs=[_comp(9, "Leaf", version=2)]))

    flat = flatten_slot(slot)

    assert flat[identity_key("ComponentDTORes", _comp(5, "Group"))] == ComponentSummary(
        component_id=5, name="Group", version=1
    )
    assert flat[identity_key("ComponentDTORes", _comp(9, "Leaf"))] == ComponentSummary(
        component_id=9, name="Leaf", version=2
    )


def test_edited_component_shows_single_change_not_remove_add():
    """Given a slot whose only component has its version bumped.

    When diffing the two payloads.
    Then a single change entry is produced and no add/remove pair.
    """
    old = {"subjectComponents": _slot(_comp(5, "Engineers", version=1))}
    new = {"subjectComponents": _slot(_comp(5, "Engineers", version=2))}

    changes = _slot_changes(diff_payloads(old, new), "subjectComponents")

    assert [change.kind for change in changes] == ["change"]
    assert changes[0].old == ComponentSummary(
        component_id=5, name="Engineers", version=1
    )
    assert changes[0].new == ComponentSummary(
        component_id=5, name="Engineers", version=2
    )


def test_added_and_removed_components_reported_by_id_and_name():
    """Given a slot where one component is replaced by another.

    When diffing the two payloads.
    Then one add and one remove are produced, each carrying id and name.
    """
    old = {"subjectComponents": _slot(_comp(5, "Engineers"))}
    new = {"subjectComponents": _slot(_comp(6, "Operations"))}

    changes = _slot_changes(diff_payloads(old, new), "subjectComponents")
    kinds = sorted(change.kind for change in changes)

    assert kinds == ["add", "remove"]
    added = next(change for change in changes if change.kind == "add")
    removed = next(change for change in changes if change.kind == "remove")
    assert added.new == ComponentSummary(component_id=6, name="Operations", version=1)
    assert removed.old == ComponentSummary(component_id=5, name="Engineers", version=1)


def test_nested_subcomponent_matched_by_id_at_depth():
    """Given an edit to a component nested via subComponents.

    When diffing the two payloads.
    Then the nested component yields a single change matched by its id.
    """
    old = {"subjectComponents": _slot(_comp(5, "Group", subs=[_comp(9, "Leaf", 1)]))}
    new = {"subjectComponents": _slot(_comp(5, "Group", subs=[_comp(9, "Leaf", 2)]))}

    changes = _slot_changes(diff_payloads(old, new), "subjectComponents")

    assert [change.kind for change in changes] == ["change"]
    assert changes[0].old == ComponentSummary(component_id=9, name="Leaf", version=1)
    assert changes[0].new == ComponentSummary(component_id=9, name="Leaf", version=2)


def test_reordered_components_yield_no_change():
    """Given two slots holding the same components in different order.

    When diffing the two payloads.
    Then no changes are reported.
    """
    old = {"subjectComponents": _slot(_comp(5, "A"), _comp(6, "B"))}
    new = {"subjectComponents": _slot(_comp(6, "B"), _comp(5, "A"))}

    changes = _slot_changes(diff_payloads(old, new), "subjectComponents")

    assert changes == []


@pytest.mark.parametrize("field", sorted(COMPONENT_SLOT_FIELDS))
def test_all_five_component_slots_share_one_code_path(field: str):
    """Given an edited component in any of the five component slots.

    When diffing the two payloads.
    Then each slot yields the same single-change identity behaviour.
    """
    old = {field: _slot(_comp(5, "Engineers", version=1))}
    new = {field: _slot(_comp(5, "Engineers", version=2))}

    changes = _slot_changes(diff_payloads(old, new), field)

    assert [change.kind for change in changes] == ["change"]


def test_component_slots_field_set_covers_all_five():
    """Given the component slot field registry.

    When inspecting it.
    Then it contains exactly the five policy component slot aliases.
    """
    assert COMPONENT_SLOT_FIELDS == frozenset(
        (
            "subjectComponents",
            "toSubjectComponents",
            "fromResourceComponents",
            "toResourceComponents",
            "actionComponents",
        )
    )
