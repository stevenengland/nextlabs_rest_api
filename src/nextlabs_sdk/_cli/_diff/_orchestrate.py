"""Diff orchestration: revision resolution, header build, and render dispatch."""

from __future__ import annotations

import json
from dataclasses import dataclass

from nextlabs_sdk._cli._diff import (
    _engine,
    _format,
    _models,
    _render_semantic,
    _render_unified,
)
from nextlabs_sdk._cli._diff._revision_select import (
    select_policy_revision,
    select_revisions,
)
from nextlabs_sdk._cli._output_format import OutputFormat
from nextlabs_sdk._cloudaz._policies import PolicyService
from nextlabs_sdk._cloudaz._policy_models import PolicyRevision


def resolve_diff_revisions(
    policies: PolicyService,
    policy_id: int,
    policy_id_b: int | None,
    *,
    from_rev: int | None,
    to_rev: int | None,
) -> tuple[PolicyRevision, PolicyRevision]:
    """Resolve the pair of revisions being compared.

    Args:
        policies: Policy service used to look up revisions.
        policy_id: First policy ID.
        policy_id_b: Second policy ID for cross-policy comparisons, if any.
        from_rev: Override the "from" revision.
        to_rev: Override the "to" revision.

    Returns:
        The ``(old, new)`` revisions to diff.
    """
    if policy_id_b is None:
        return select_revisions(policies, policy_id, from_rev=from_rev, to_rev=to_rev)
    old = select_policy_revision(policies, policy_id, revision=from_rev)
    new = select_policy_revision(policies, policy_id_b, revision=to_rev)
    return old, new


def build_diff_header(
    old: PolicyRevision, new: PolicyRevision, *, cross_policy: bool
) -> _models.DiffHeader:
    """Build the header describing what is being compared.

    Args:
        old: The "from" revision.
        new: The "to" revision.
        cross_policy: Whether this compares two distinct policies.

    Returns:
        The diff header for rendering.
    """
    if cross_policy:
        return _models.DiffHeader(
            policy_name=old.policy_detail.name,
            policy_id=old.policy_detail.id,
            from_rev=old.revision,
            to_rev=new.revision,
            to_policy_name=new.policy_detail.name,
            to_policy_id=new.policy_detail.id,
        )
    return _models.DiffHeader(
        policy_name=new.policy_detail.name,
        policy_id=new.policy_detail.id,
        from_rev=old.revision,
        to_rev=new.revision,
    )


@dataclass(frozen=True)
class DiffRenderOptions:
    """Options controlling how a policy diff is computed and rendered.

    Attributes:
        cross_policy: Whether this compares two distinct policies.
        show_all: Whether to reveal ordering and noise differences.
        output_format: The CLI-wide output format (e.g. JSON).
        diff_format: The human renderer to use when not in JSON mode.
    """

    cross_policy: bool
    show_all: bool
    output_format: OutputFormat
    diff_format: _format.DiffFormat


def render_diff(
    old: PolicyRevision, new: PolicyRevision, options: DiffRenderOptions
) -> _models.DiffResult:
    """Diff two revisions and render the result in the requested format.

    Args:
        old: The "from" revision.
        new: The "to" revision.
        options: Options controlling how the diff is computed and rendered.

    Returns:
        The computed diff result, so callers can inspect it (e.g. for
        ``--exit-code`` handling).
    """
    old_payload = old.policy_detail.model_dump(mode="json", by_alias=True)
    new_payload = new.policy_detail.model_dump(mode="json", by_alias=True)
    diff_result = _engine.diff_payloads(
        old_payload,
        new_payload,
        show_all=options.show_all,
        cross_policy=options.cross_policy,
    )
    header = build_diff_header(old, new, cross_policy=options.cross_policy)
    if options.output_format is OutputFormat.JSON:
        print(json.dumps(_models.diff_result_to_dict(diff_result), indent=2))
    elif options.diff_format is _format.DiffFormat.UNIFIED:
        _render_unified.render_unified(
            _render_unified.UnifiedDiffInput(
                old=old_payload,
                new=new_payload,
                header=header,
                diff_result=diff_result,
            ),
            show_all=options.show_all,
        )
    else:
        _render_semantic.render_semantic(diff_result, header, show_all=options.show_all)
    return diff_result
