from __future__ import annotations

import pytest
from mockito import mock, verify, when

from nextlabs_sdk._cli._diff._revision_select import (
    InsufficientRevisionsError,
    UnknownRevisionError,
    select_revisions,
)
from nextlabs_sdk.cloudaz import (
    Policy,
    PolicyHistoryEntry,
    PolicyRevision,
    PolicyService,
)

POLICY_ID = 82


def _entry(revision: int, entry_id: int, action_type: str = "DE") -> PolicyHistoryEntry:
    return PolicyHistoryEntry(id=entry_id, revision=revision, action_type=action_type)


def _revision(revision: int, entry_id: int) -> PolicyRevision:
    return PolicyRevision(
        id=entry_id,
        revision=revision,
        action_type="DE",
        policy_detail=Policy(
            id=POLICY_ID, name="P", status="DRAFT", effect_type="ALLOW"
        ),
    )


def test_default_selects_two_most_recent_deployed_by_entry_id():
    """Given history with deployed entries whose ids differ from the policy id.

    When selecting with no overrides.
    Then each revision is fetched via get_revision using the entry's own id,
        never the policy id, with the newest deployed revision as "new".
    """
    # given
    policies = mock(PolicyService)
    when(policies).list_history(POLICY_ID).thenReturn(
        [
            _entry(1, entry_id=101),
            _entry(2, entry_id=102),
            _entry(3, entry_id=103),
            _entry(4, entry_id=104, action_type="DR"),
        ]
    )
    when(policies).get_revision(103, 3).thenReturn(_revision(3, entry_id=103))
    when(policies).get_revision(102, 2).thenReturn(_revision(2, entry_id=102))
    # when
    old, new = select_revisions(policies, POLICY_ID)
    # then
    assert old.revision == 2
    assert new.revision == 3
    verify(policies).get_revision(102, 2)
    verify(policies).get_revision(103, 3)


def test_from_and_to_overrides_resolve_entry_ids_and_bypass_deployed_filter():
    """Given history of non-deployed entries whose ids differ from the policy id.

    When overriding both sides with explicit revision numbers.
    Then those revisions are resolved to their entries' ids and fetched with
        those ids, despite none being deployed.
    """
    # given
    policies = mock(PolicyService)
    when(policies).list_history(POLICY_ID).thenReturn(
        [
            _entry(5, entry_id=205, action_type="DR"),
            _entry(6, entry_id=206, action_type="DR"),
        ]
    )
    when(policies).get_revision(205, 5).thenReturn(_revision(5, entry_id=205))
    when(policies).get_revision(206, 6).thenReturn(_revision(6, entry_id=206))
    # when
    old, new = select_revisions(policies, POLICY_ID, from_rev=5, to_rev=6)
    # then
    assert old.revision == 5
    assert new.revision == 6
    verify(policies).get_revision(205, 5)
    verify(policies).get_revision(206, 6)


def test_overridden_revision_absent_from_history_raises():
    """Given history that does not contain an explicitly requested revision.

    When overriding with a revision number absent from the policy's history.
    Then a clear domain error is raised instead of fetching a revision.
    """
    # given
    policies = mock(PolicyService)
    when(policies).list_history(POLICY_ID).thenReturn(
        [_entry(5, entry_id=205, action_type="DR")]
    )
    # when / then
    with pytest.raises(UnknownRevisionError):
        select_revisions(policies, POLICY_ID, from_rev=5, to_rev=9)


def test_fewer_than_two_comparable_raises():
    """Given history with a single deployed revision and no overrides.

    When selecting.
    Then a clear domain error is raised.
    """
    # given
    policies = mock(PolicyService)
    when(policies).list_history(POLICY_ID).thenReturn([_entry(1, entry_id=101)])
    # when / then
    with pytest.raises(InsufficientRevisionsError):
        select_revisions(policies, POLICY_ID)


from nextlabs_sdk._cli._diff._revision_select import select_policy_revision


def test_select_policy_revision_defaults_to_latest_deployed():
    """Given a policy whose history has several deployed revisions.

    When resolving a single side with no explicit revision.
    Then the newest deployed revision is fetched via its own entry id.
    """
    # given
    policies = mock(PolicyService)
    when(policies).list_history(POLICY_ID).thenReturn(
        [
            _entry(1, entry_id=101),
            _entry(3, entry_id=103),
            _entry(2, entry_id=102),
            _entry(4, entry_id=104, action_type="DR"),
        ]
    )
    when(policies).get_revision(103, 3).thenReturn(_revision(3, entry_id=103))
    # when
    revision = select_policy_revision(policies, POLICY_ID)
    # then
    assert revision.revision == 3
    verify(policies).get_revision(103, 3)


def test_select_policy_revision_uses_explicit_override():
    """Given a policy whose requested revision is not deployed.

    When resolving a single side with an explicit revision number.
    Then that revision is fetched, bypassing the deployed-only filter.
    """
    # given
    policies = mock(PolicyService)
    when(policies).list_history(POLICY_ID).thenReturn(
        [_entry(7, entry_id=207, action_type="DR")]
    )
    when(policies).get_revision(207, 7).thenReturn(_revision(7, entry_id=207))
    # when
    revision = select_policy_revision(policies, POLICY_ID, revision=7)
    # then
    assert revision.revision == 7
    verify(policies).get_revision(207, 7)


def test_select_policy_revision_no_deployed_raises():
    """Given a policy with no deployed revision and no override.

    When resolving a single side.
    Then a clear domain error is raised.
    """
    # given
    policies = mock(PolicyService)
    when(policies).list_history(POLICY_ID).thenReturn(
        [_entry(1, entry_id=101, action_type="DR")]
    )
    # when / then
    with pytest.raises(InsufficientRevisionsError):
        select_policy_revision(policies, POLICY_ID)
