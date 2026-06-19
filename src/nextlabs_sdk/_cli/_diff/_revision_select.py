"""Revision selection logic for the policy diff command."""

from __future__ import annotations

from nextlabs_sdk._cloudaz._policies import PolicyService
from nextlabs_sdk._cloudaz._policy_models import PolicyRevision
from nextlabs_sdk.exceptions import NextLabsError

DEPLOYED_ACTION_TYPE = "DE"


class InsufficientRevisionsError(NextLabsError):
    """Raised when fewer than two comparable revisions exist for a policy."""


def select_revisions(
    policies: PolicyService,
    policy_id: int,
    *,
    from_rev: int | None = None,
    to_rev: int | None = None,
) -> tuple[PolicyRevision, PolicyRevision]:
    """Resolve the two policy revisions to compare.

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
        InsufficientRevisionsError: When both sides cannot be resolved because
            fewer than two deployed revisions exist and overrides do not supply
            both sides.
    """
    if from_rev is not None and to_rev is not None:
        old = policies.get_revision(policy_id, from_rev)
        new = policies.get_revision(policy_id, to_rev)
        return old, new

    entries = policies.list_history(policy_id)
    deployed = sorted(
        (entry for entry in entries if entry.action_type == DEPLOYED_ACTION_TYPE),
        key=lambda entry: entry.revision,
        reverse=True,
    )

    resolved_to = to_rev
    resolved_from = from_rev

    if resolved_to is None:
        if not deployed:
            raise InsufficientRevisionsError(
                f"Policy {policy_id} has fewer than two comparable revisions to diff."
            )
        resolved_to = deployed[0].revision

    if resolved_from is None:
        remaining = [entry for entry in deployed if entry.revision != resolved_to]
        if not remaining:
            raise InsufficientRevisionsError(
                f"Policy {policy_id} has fewer than two comparable revisions to diff."
            )
        resolved_from = remaining[0].revision

    old = policies.get_revision(policy_id, resolved_from)
    new = policies.get_revision(policy_id, resolved_to)
    return old, new
