import pytest
from mockito import mock, when

from nextlabs_sdk.cloudaz import (
    Policy,
    PolicyHistoryEntry,
    PolicyRevision,
    PolicyService,
)
from nextlabs_sdk._cli._diff._revision_select import (
    InsufficientRevisionsError,
    select_revisions,
)


def _entry(revision: int, action_type: str = "DE") -> PolicyHistoryEntry:
    return PolicyHistoryEntry(id=10, revision=revision, action_type=action_type)


def _revision(revision: int) -> PolicyRevision:
    return PolicyRevision(
        id=10,
        revision=revision,
        action_type="DE",
        policy_detail=Policy(id=82, name="P", status="DRAFT", effect_type="ALLOW"),
    )


def test_default_selects_two_most_recent_deployed():
    """Given history with three deployed revisions and one draft.

    When selecting with no overrides.
    Then the two most recent deployed revisions are chosen, newest as "new".
    """
    # given
    policies = mock(PolicyService)
    when(policies).list_history(10).thenReturn(
        [_entry(1), _entry(2), _entry(3), _entry(4, action_type="DR")]
    )
    when(policies).get_revision(10, 3).thenReturn(_revision(3))
    when(policies).get_revision(10, 2).thenReturn(_revision(2))
    # when
    old, new = select_revisions(policies, 10)
    # then
    assert old.revision == 2
    assert new.revision == 3


def test_from_and_to_override_bypass_deployed_filter():
    """Given history whose entries are all non-deployed drafts.

    When overriding both sides explicitly.
    Then those exact revisions are fetched despite none being deployed.
    """
    # given
    policies = mock(PolicyService)
    when(policies).list_history(10).thenReturn(
        [_entry(5, action_type="DR"), _entry(6, action_type="DR")]
    )
    when(policies).get_revision(10, 5).thenReturn(_revision(5))
    when(policies).get_revision(10, 6).thenReturn(_revision(6))
    # when
    old, new = select_revisions(policies, 10, from_rev=5, to_rev=6)
    # then
    assert old.revision == 5
    assert new.revision == 6


def test_fewer_than_two_comparable_raises():
    """Given history with a single deployed revision and no overrides.

    When selecting.
    Then a clear domain error is raised.
    """
    # given
    policies = mock(PolicyService)
    when(policies).list_history(10).thenReturn([_entry(1)])
    # when / then
    with pytest.raises(InsufficientRevisionsError):
        select_revisions(policies, 10)
