from __future__ import annotations

from typing import Any

import pytest

from nextlabs_sdk._cli._diff._engine import diff_payloads
from nextlabs_sdk._cli._diff._identity import (
    COMPONENT_SLOT_FIELDS,
    OBLIGATION_FIELDS,
    TAG_FIELDS,
    ComponentSummary,
    ObligationSummary,
    TagSummary,
    flatten_slot,
    identity_key,
    pair_obligations,
    pair_tags,
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


def _obl(
    name: str,
    params: dict[str, str],
    policy_model_id: int = 0,
    obligation_id: int | None = None,
) -> dict[str, Any]:
    return {
        "id": obligation_id,
        "policyModelId": policy_model_id,
        "name": name,
        "params": params,
    }


def _obligation_changes(result: Any, field: str) -> list[Any]:
    return [
        change for change in result.changes if change.path and change.path[0] == field
    ]


def test_obligation_fields_cover_allow_and_deny():
    """Given the obligation field registry.

    When inspecting it.
    Then it contains exactly the allow and deny obligation aliases.
    """
    assert OBLIGATION_FIELDS == frozenset(("allowObligations", "denyObligations"))


def test_obligations_sharing_a_name_are_paired_positionally():
    """Given two obligations with the same (name, policyModelId).

    When pairing the old and new obligation lists.
    Then they are matched positionally within the colliding group.
    """
    old = [_obl("data_masking", {"col": "ssn"}), _obl("data_masking", {"col": "dob"})]
    new = [_obl("data_masking", {"col": "ssn2"}), _obl("data_masking", {"col": "dob2"})]

    pairs = pair_obligations(old, new)

    assert len(pairs) == 2
    old_cols: list[object] = []
    new_cols: list[object] = []
    for old_obl, new_obl in pairs:
        assert old_obl is not None and new_obl is not None
        old_params = old_obl["params"]
        new_params = new_obl["params"]
        assert isinstance(old_params, dict) and isinstance(new_params, dict)
        old_cols.append(old_params["col"])
        new_cols.append(new_params["col"])
    assert old_cols == ["ssn", "dob"]
    assert new_cols == ["ssn2", "dob2"]


def test_both_shared_name_obligations_have_their_param_changes_reported():
    """Given two same-name obligations each with a changed param.

    When diffing the two payloads.
    Then both param changes are reported and none is dropped.
    """
    old = {
        "allowObligations": [
            _obl("data_masking", {"col": "ssn"}),
            _obl("data_masking", {"col": "dob"}),
        ]
    }
    new = {
        "allowObligations": [
            _obl("data_masking", {"col": "ssn_hash"}),
            _obl("data_masking", {"col": "dob_hash"}),
        ]
    }

    changes = _obligation_changes(diff_payloads(old, new), "allowObligations")
    kinds = [change.kind for change in changes]

    assert kinds == ["change", "change"]
    assert sorted(change.new for change in changes) == ["dob_hash", "ssn_hash"]


def test_changed_obligation_param_is_reported_as_a_scalar_string_change():
    """Given an obligation whose param value changes.

    When diffing the two payloads.
    Then a scalar string change is produced for the changed param.
    """
    old = {"allowObligations": [_obl("redact", {"fields": "name email"})]}
    new = {"allowObligations": [_obl("redact", {"fields": "name phone"})]}

    changes = _obligation_changes(diff_payloads(old, new), "allowObligations")

    assert [change.kind for change in changes] == ["change"]
    assert changes[0].old == "name email"
    assert changes[0].new == "name phone"
    assert changes[0].path[-1] == "fields"


def test_added_and_removed_obligations_are_reported():
    """Given one obligation replaced by a differently-named obligation.

    When diffing the two payloads.
    Then one add and one remove summary header are produced, each carrying the
    name (the expanded content lines nest beneath them).
    """
    old = {"denyObligations": [_obl("log", {"level": "info"})]}
    new = {"denyObligations": [_obl("alert", {"channel": "ops"})]}

    changes = _obligation_changes(diff_payloads(old, new), "denyObligations")
    headers = [change for change in changes if change.path == ("denyObligations",)]
    kinds = sorted(change.kind for change in headers)

    assert kinds == ["add", "remove"]
    added = next(change for change in headers if change.kind == "add")
    removed = next(change for change in headers if change.kind == "remove")
    assert added.new == ObligationSummary(name="alert")
    assert removed.old == ObligationSummary(name="log")


def test_extra_obligation_in_colliding_group_is_reported_as_added():
    """Given a colliding-name group that gains an extra obligation.

    When diffing the two payloads.
    Then the unpaired obligation's summary header is reported as added, not a
    change.
    """
    old = {"allowObligations": [_obl("data_masking", {"col": "a"})]}
    new = {
        "allowObligations": [
            _obl("data_masking", {"col": "a"}),
            _obl("data_masking", {"col": "b"}),
        ]
    }

    changes = _obligation_changes(diff_payloads(old, new), "allowObligations")
    headers = [change for change in changes if change.path == ("allowObligations",)]

    assert [change.kind for change in headers] == ["add"]
    assert headers[0].new == ObligationSummary(name="data_masking")


def test_tag_identity_key_prefers_key_then_label():
    """Given tags with key, with only label, and with neither.

    When resolving each tag's identity key for schema type 'Tag'.
    Then key wins, label is the fallback, and neither yields None.
    """
    # given / when / then
    assert identity_key("Tag", {"key": "adr6", "label": "ADR6"}) == ("key", "adr6")
    assert identity_key("Tag", {"label": "ADR6"}) == ("label", "ADR6")
    assert identity_key("Tag", {}) is None


def test_tag_fields_contains_tags_alias():
    """Given the tag field registry.

    When inspecting it.
    Then it contains exactly the tags field alias.
    """
    assert TAG_FIELDS == frozenset(("tags",))


def test_tag_summary_holds_key_and_label():
    """Given a tag identity summary.

    When constructing a TagSummary.
    Then key and label are stored as-is.
    """
    # given / when
    summary = TagSummary(key="adr6", label="ADR6")

    # then
    assert summary.key == "adr6"
    assert summary.label == "ADR6"


def test_pair_tags_matches_by_key_falling_back_to_label():
    """Given two tag lists matched by key and by label.

    When pairing them.
    Then key-identity and label-identity tags are each paired exactly once.
    """
    # given
    old = [{"key": "adr6", "label": "ADR6"}, {"label": "STATUS"}]
    new = [{"key": "adr6", "label": "ADR6"}, {"label": "STATUS", "status": "ON"}]

    # when
    pairs = pair_tags(old, new)

    # then
    assert len(pairs) == 2
    for old_tag, new_tag in pairs:
        assert old_tag is not None
        assert new_tag is not None
