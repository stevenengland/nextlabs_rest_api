"""Revision selection logic for the policy diff command."""

from __future__ import annotations

from nextlabs_sdk._cloudaz._policies import PolicyService
from nextlabs_sdk._cloudaz._policy_models import PolicyHistoryEntry, PolicyRevision
from nextlabs_sdk.exceptions import NextLabsError

DEPLOYED_ACTION_TYPE = "DE"


class InsufficientRevisionsError(NextLabsError):
    """Raised when fewer than two comparable revisions exist for a policy."""


class UnknownRevisionError(NextLabsError):
    """Raised when a requested revision number is absent from a policy's history."""


def select_revisions(
    policies: PolicyService,
    policy_id: int,
    *,
    from_rev: int | None = None,
    to_rev: int | None = None,
) -> tuple[PolicyRevision, PolicyRevision]:
    """Resolve the two policy revisions to compare.

    Each side is fetched with the history entry's own ``id`` as the revision-ID
    path segment, never the policy ID, because the server addresses a revision
    by that entry ``id``.

    Args:
        policies: The policy service used to query history and fetch revisions.
        policy_id: The policy whose revisions are being compared.
        from_rev: Explicit revision number for the older side. When given,
            bypasses the deployed-only filter for that side.
        to_rev: Explicit revision number for the newer side. When given,
            bypasses the deployed-only filter for that side.

    Returns:
        A ``(old, new)`` tuple where ``new`` is the newer/``to`` side.

    Raises:
        InsufficientRevisionsError: When a side cannot be auto-selected because
            fewer than two deployed revisions exist and overrides do not supply
            it.
        UnknownRevisionError: When an explicitly overridden revision number is
            absent from the policy's history.
    """
    entries = policies.list_history(policy_id)
    by_revision = {entry.revision: entry for entry in entries}

    resolved_to = _resolve_to(entries, policy_id, to_rev)
    resolved_from = _resolve_from(entries, policy_id, from_rev, resolved_to)

    old_entry = _require_entry(by_revision, policy_id, resolved_from)
    new_entry = _require_entry(by_revision, policy_id, resolved_to)

    old = policies.get_revision(old_entry.id, old_entry.revision)
    new = policies.get_revision(new_entry.id, new_entry.revision)
    return old, new


def _deployed_newest_first(
    entries: list[PolicyHistoryEntry],
) -> list[PolicyHistoryEntry]:
    return sorted(
        (entry for entry in entries if entry.action_type == DEPLOYED_ACTION_TYPE),
        key=lambda entry: entry.revision,
        reverse=True,
    )


def _resolve_to(
    entries: list[PolicyHistoryEntry],
    policy_id: int,
    to_rev: int | None,
) -> int:
    if to_rev is not None:
        return to_rev
    deployed = _deployed_newest_first(entries)
    if not deployed:
        raise InsufficientRevisionsError(
            f"Policy {policy_id} has fewer than two comparable revisions to diff."
        )
    return deployed[0].revision


def _resolve_from(
    entries: list[PolicyHistoryEntry],
    policy_id: int,
    from_rev: int | None,
    resolved_to: int,
) -> int:
    if from_rev is not None:
        return from_rev
    remaining = [
        entry
        for entry in _deployed_newest_first(entries)
        if entry.revision != resolved_to
    ]
    if not remaining:
        raise InsufficientRevisionsError(
            f"Policy {policy_id} has fewer than two comparable revisions to diff."
        )
    return remaining[0].revision


def _require_entry(
    by_revision: dict[int, PolicyHistoryEntry],
    policy_id: int,
    revision: int,
) -> PolicyHistoryEntry:
    entry = by_revision.get(revision)
    if entry is None:
        raise UnknownRevisionError(
            f"Revision {revision} is not in policy {policy_id}'s history."
        )
    return entry
