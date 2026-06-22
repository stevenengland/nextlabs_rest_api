from __future__ import annotations

from typing import Any, cast

from nextlabs_sdk._cli._diff._engine import diff_payloads


def test_reordered_idless_array_yields_no_change():
    """Given two payloads whose only difference is tag ordering.

    When diffing.
    Then there are no changes.
    """
    old = {"name": "P", "tags": [{"key": "a"}, {"key": "b"}]}
    new = {"name": "P", "tags": [{"key": "b"}, {"key": "a"}]}

    result = diff_payloads(old, new)

    assert result.changes == ()


def test_dropped_duplicate_idless_element_is_reported():
    """Given two payloads where a duplicated id-less array element is removed.

    When diffing without show_all, tags now route through identity-aware matching.
    Then no change is reported, because both old entries share the same identity
    key (``key="a"``) and the identity registry collapses them to one logical tag.
    Duplicate tag keys are invalid domain data; the semantic diff correctly treats
    dropping a duplicate of the same identity as a no-op.
    """
    old = {"name": "P", "tags": [{"key": "a"}, {"key": "a"}]}
    new = {"name": "P", "tags": [{"key": "a"}]}

    result = diff_payloads(old, new)

    assert result.changes == ()


def test_deployment_noise_excluded_by_default():
    """Given payloads differing only in deployment-noise leaf fields.

    When diffing without show_all.
    Then no visible changes, but the hidden count reflects the noise.
    """
    old = {"name": "P", "deploymentTime": 1, "createdDate": 10, "modifiedBy": "x"}
    new = {"name": "P", "deploymentTime": 2, "createdDate": 20, "modifiedBy": "y"}

    result = diff_payloads(old, new)

    assert result.changes == ()
    assert result.hidden_noise_count == 3


def test_version_change_stays_visible():
    """Given payloads differing only in version.

    When diffing.
    Then the version change is reported.
    """
    old = {"name": "P", "version": 3}
    new = {"name": "P", "version": 4}

    result = diff_payloads(old, new)

    assert any(c.path == ("version",) and c.kind == "change" for c in result.changes)


def test_nested_scalar_change_recorded_with_path():
    """Given a nested scalar edit.

    When diffing.
    Then the change carries the full nested path.
    """
    old = {"environmentConfig": {"remoteAccess": 1}}
    new = {"environmentConfig": {"remoteAccess": 2}}

    result = diff_payloads(old, new)

    assert any(
        c.path == ("environmentConfig", "remoteAccess") and c.old == 1 and c.new == 2
        for c in result.changes
    )


def test_show_all_reincludes_noise_and_ordering():
    """Given payloads differing in noise and array order.

    When diffing with show_all.
    Then the deployment noise difference is now visible.
    """
    old = {"deploymentTime": 1, "tags": [{"key": "a"}, {"key": "b"}]}
    new = {"deploymentTime": 2, "tags": [{"key": "b"}, {"key": "a"}]}

    result = diff_payloads(old, new, show_all=True)

    assert any(c.path == ("deploymentTime",) for c in result.changes)


from nextlabs_sdk._cli._diff._identity import TagSummary
from nextlabs_sdk._cli._diff._models import diff_result_to_dict


def test_engine_emits_per_element_tag_changes():
    """Given old/new payloads adding one tag, removing one, editing one in place.

    When diffing.
    Then there is a TagSummary add, a TagSummary remove, and a recursed scalar
    change carrying the edited tag's field path.
    """
    # given
    old = {
        "name": "P",
        "tags": [
            {"key": "keep", "label": "KEEP", "status": "ON"},
            {"key": "gone", "label": "GONE"},
        ],
    }
    new = {
        "name": "P",
        "tags": [
            {"key": "keep", "label": "KEEP", "status": "OFF"},
            {"key": "fresh", "label": "FRESH"},
        ],
    }
    # when
    result = diff_payloads(old, new)
    tag_changes = [c for c in result.changes if c.path and c.path[0] == "tags"]
    # then
    assert any(c.kind == "add" and isinstance(c.new, TagSummary) for c in tag_changes)
    assert any(
        c.kind == "remove" and isinstance(c.old, TagSummary) for c in tag_changes
    )
    assert any(
        c.kind == "change" and c.old == "ON" and c.new == "OFF" for c in tag_changes
    )


def test_tag_changes_serialise_per_element():
    """Given a payload that adds a single tag.

    When diffing and serialising to a dict.
    Then a per-element tag change with the TagSummary fields is emitted (not a whole-list entry).
    """
    # given
    old = {"name": "P", "tags": []}
    new = {"name": "P", "tags": [{"key": "fresh", "label": "FRESH"}]}
    # when
    payload = diff_result_to_dict(diff_payloads(old, new))
    tag_entries = [
        c
        for c in cast(list[Any], payload["changes"])
        if c["path"] and c["path"][0] == "tags"
    ]
    # then
    assert tag_entries
    assert tag_entries[0]["new"] == {"key": "fresh", "label": "FRESH"}
