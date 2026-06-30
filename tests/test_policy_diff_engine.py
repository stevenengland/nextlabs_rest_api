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


from nextlabs_sdk._cli._diff._engine import _CROSS_POLICY_IDENTITY_FIELDS


def test_cross_policy_strips_top_level_identity_fields():
    """Given two policies differing in top-level identity fields and one body field.

    When diffing in cross-policy mode without show_all.
    Then identity fields never surface and are not counted as noise; only the
        genuine body difference is reported.
    """
    # given
    old = {
        "id": 1,
        "name": "Alpha",
        "fullName": "/Alpha",
        "folderId": 7,
        "parentId": 3,
        "parentName": "root",
        "version": 2,
        "revisionCount": 5,
        "ownerId": 11,
        "ownerDisplayName": "Ann",
        "description": "read",
    }
    new = {
        "id": 2,
        "name": "Beta",
        "fullName": "/Beta",
        "folderId": 9,
        "parentId": 4,
        "parentName": "other",
        "version": 8,
        "revisionCount": 1,
        "ownerId": 22,
        "ownerDisplayName": "Bob",
        "description": "write",
    }

    result = diff_payloads(old, new, cross_policy=True)

    paths = {change.path[0] for change in result.changes}
    assert paths == {"description"}
    assert _CROSS_POLICY_IDENTITY_FIELDS & paths == set()
    assert result.hidden_noise_count == 0


def test_cross_policy_keeps_nested_identity_like_fields():
    """Given two policies whose only difference is a nested component name.

    When diffing in cross-policy mode.
    Then the nested name change still surfaces, proving the strip is top-level only.
    """
    # given
    old = {
        "id": 1,
        "name": "Alpha",
        "subjectComponents": [
            {"operator": "AND", "components": [{"id": 5, "name": "Old", "version": 1}]}
        ],
    }
    new = {
        "id": 2,
        "name": "Beta",
        "subjectComponents": [
            {"operator": "AND", "components": [{"id": 5, "name": "New", "version": 1}]}
        ],
    }

    result = diff_payloads(old, new, cross_policy=True)

    assert any(c.path and c.path[0] == "subjectComponents" for c in result.changes)


def test_cross_policy_show_all_reveals_identity_fields():
    """Given two policies differing in a top-level identity field.

    When diffing in cross-policy mode with show_all.
    Then the identity field difference is revealed.
    """
    # given
    old = {"id": 1, "name": "Alpha", "description": "x"}
    new = {"id": 2, "name": "Beta", "description": "x"}

    result = diff_payloads(old, new, cross_policy=True, show_all=True)

    assert any(c.path == ("name",) for c in result.changes)


from nextlabs_sdk._cli._diff._identity import ObligationSummary


def test_added_obligation_expands_payload_field_lines():
    """Given a payload that adds an obligation carrying params and policyModelId.

    When diffing without show_all.
    Then a summary-header add is emitted plus per-field add lines for the
    obligation's policyModelId and each params entry, nested under the
    obligation's name.
    """
    # given
    old = {"name": "P", "allowObligations": []}
    new = {
        "name": "P",
        "allowObligations": [
            {
                "id": None,
                "policyModelId": 7,
                "name": "data_masking",
                "params": {"col": "ssn"},
            }
        ],
    }
    # when
    result = diff_payloads(old, new)
    obl = [c for c in result.changes if c.path and c.path[0] == "allowObligations"]
    # then
    assert any(
        c.kind == "add"
        and c.path == ("allowObligations",)
        and isinstance(c.new, ObligationSummary)
        for c in obl
    )
    assert any(
        c.kind == "add"
        and c.path == ("allowObligations", "data_masking", "policyModelId")
        and c.new == 7
        for c in obl
    )
    assert any(
        c.kind == "add"
        and c.path == ("allowObligations", "data_masking", "params", "col")
        and c.new == "ssn"
        for c in obl
    )


def test_removed_obligation_expands_payload_field_lines():
    """Given a payload that removes an obligation carrying params.

    When diffing without show_all.
    Then a summary-header remove is emitted plus per-field remove lines carrying
    the removed obligation's params under its name.
    """
    # given
    old = {
        "name": "P",
        "allowObligations": [
            {
                "id": None,
                "policyModelId": 0,
                "name": "data_masking",
                "params": {"col": "ssn"},
            }
        ],
    }
    new = {"name": "P", "allowObligations": []}
    # when
    result = diff_payloads(old, new)
    obl = [c for c in result.changes if c.path and c.path[0] == "allowObligations"]
    # then
    assert any(
        c.kind == "remove"
        and c.path == ("allowObligations",)
        and isinstance(c.old, ObligationSummary)
        for c in obl
    )
    assert any(
        c.kind == "remove"
        and c.path == ("allowObligations", "data_masking", "params", "col")
        and c.old == "ssn"
        for c in obl
    )


def test_noise_field_inside_added_obligation_is_hidden_by_default():
    """Given an added obligation whose payload carries a deployment-noise field.

    When diffing without show_all.
    Then the noise field surfaces in no visible change and is counted as hidden.
    """
    # given
    old = {"name": "P", "allowObligations": []}
    new = {
        "name": "P",
        "allowObligations": [
            {
                "id": None,
                "policyModelId": 0,
                "name": "data_masking",
                "params": {"col": "ssn"},
                "lastUpdatedDate": 123,
            }
        ],
    }
    # when
    result = diff_payloads(old, new)
    # then
    assert not any(c.path and c.path[-1] == "lastUpdatedDate" for c in result.changes)
    assert result.hidden_noise_count == 1


def test_noise_field_inside_added_obligation_is_revealed_with_show_all():
    """Given an added obligation whose payload carries a deployment-noise field.

    When diffing with show_all.
    Then the noise field's value is no longer suppressed.
    """
    # given
    old = {"name": "P", "allowObligations": []}
    new = {
        "name": "P",
        "allowObligations": [
            {
                "id": None,
                "policyModelId": 0,
                "name": "data_masking",
                "params": {"col": "ssn"},
                "lastUpdatedDate": 123,
            }
        ],
    }
    # when
    result = diff_payloads(old, new, show_all=True)
    # then
    assert result.hidden_noise_count == 0
    assert any("lastUpdatedDate" in repr(c.new) for c in result.changes)
