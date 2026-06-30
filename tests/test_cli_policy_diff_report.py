from __future__ import annotations

from typing import Any

import pytest
from mockito import when
from strip_ansi import strip_ansi

from nextlabs_sdk._cli._app import app
from nextlabs_sdk.cloudaz import PolicyHistoryEntry

from tests._policy_diff_helpers import (
    GLOBAL_OPTS,
    component,
    entry,
    make_stub,
    obligation,
    revision,
    revision_with_obligations,
    revision_with_subjects,
    runner,
)


@pytest.fixture
def stub() -> tuple[Any, Any]:
    return make_stub()


def test_edited_component_renders_single_modified_entry(stub: tuple[Any, Any]) -> None:
    """Given two revisions where a subject component's version is bumped, when
    running diff, then it shows a single modified entry by name and id, not a
    remove-plus-add."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision_with_subjects(2, [component(5, "Engineers", version=1)])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision_with_subjects(3, [component(5, "Engineers", version=2)])
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "Engineers (id=5)" in output
    assert "v1" in output and "v2" in output
    assert "- subjectComponents" not in output
    assert "+ subjectComponents" not in output


def test_added_and_removed_components_render_by_name_and_id(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions where a subject component is replaced, when running
    diff, then both the added and removed components are shown by name and
    id."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision_with_subjects(2, [component(5, "Engineers")])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision_with_subjects(3, [component(6, "Operations")])
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "Engineers (id=5)" in output
    assert "Operations (id=6)" in output


def test_diff_default_renders_semantic_report(stub: tuple[Any, Any]) -> None:
    """Given two deployed revisions differing in description, when running diff
    with no flags, then it succeeds and shows the changed scalar."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision(2, description="allow read access")
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "write" in output


def test_diff_format_semantic_renders_semantic_report(stub: tuple[Any, Any]) -> None:
    """Given two deployed revisions differing in description, when running diff
    with --format semantic, then it renders the semantic report showing the
    changed scalar."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision(2, description="allow read access")
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "policies", "diff", "10", "--format", "semantic"]
    )
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "Policy diff" not in output
    assert "write" in output


def test_diff_semantic_shows_identity_header(stub: tuple[Any, Any]) -> None:
    """Given two deployed revisions, when running diff in the default semantic
    format, then the output names the policy and the two compared revisions
    above the change sections."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision(2, description="allow read access")
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "Policy: P (id=82)" in output
    assert "Comparing revisions 2 → 3" in output
    assert output.index("Policy: P (id=82)") < output.index("description")


def test_diff_unified_shows_policy_row_and_git_revision_labels(
    stub: tuple[Any, Any],
) -> None:
    """Given two deployed revisions, when running diff with --format unified,
    then the output carries the policy identity row and the git revision labels
    derived from the compared revision numbers."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision(2, description="allow read access")
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "policies", "diff", "10", "--format", "unified"]
    )
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "Policy: P (id=82)" in output
    assert "--- revision 2" in output
    assert "+++ revision 3" in output


def test_diff_format_unified_renders_git_style_diff(stub: tuple[Any, Any]) -> None:
    """Given two deployed revisions differing in description, when running diff
    with --format unified, then it renders a git-style unified diff with a hunk
    header and the changed value on an added line."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision(2, description="allow read access")
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "policies", "diff", "10", "--format", "unified"]
    )
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "@@" in output
    assert any(line.startswith("+") and "write" in line for line in output.splitlines())


def test_diff_show_all_reveals_noise(stub: tuple[Any, Any]) -> None:
    """Given two deployed revisions differing only in a deployment-noise field,
    when running diff with --show-all, then the otherwise-hidden noise field is
    revealed."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(revision(3, deployment_time=200))
    when(mock_policies).get_revision(10, 2).thenReturn(revision(2, deployment_time=100))
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10", "--show-all"])
    assert result.exit_code == 0
    assert "deploymentTime" in strip_ansi(result.output)


def test_diff_from_to_override_fetches_those_revisions(stub: tuple[Any, Any]) -> None:
    """Given explicit from/to revisions, when overriding both sides, then it
    succeeds using the overridden revisions."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn(
        [
            PolicyHistoryEntry(id=21, revision=1, action_type="DR"),
            PolicyHistoryEntry(id=24, revision=4, action_type="DR"),
        ]
    )
    when(mock_policies).get_revision(21, 1).thenReturn(
        revision(1, description="allow read access")
    )
    when(mock_policies).get_revision(24, 4).thenReturn(
        revision(4, description="allow write access")
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "policies", "diff", "10", "--from", "1", "--to", "4"]
    )
    assert result.exit_code == 0
    assert "write" in strip_ansi(result.output)


def test_diff_too_few_revisions_exits_nonzero_without_traceback(
    stub: tuple[Any, Any],
) -> None:
    """Given a policy with only one deployed revision, when running diff, then
    it exits non-zero with a clear message and no traceback."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(3)])
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code != 0
    output = strip_ansi(result.output)
    assert "Traceback" not in output
    assert "fewer than two" in output.lower()


def test_diff_unknown_override_revision_exits_nonzero_without_traceback(
    stub: tuple[Any, Any],
) -> None:
    """Given an overridden revision absent from history, when running diff, then
    it exits non-zero with a clear message and no traceback."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "policies", "diff", "10", "--from", "2", "--to", "9"]
    )
    assert result.exit_code != 0
    output = strip_ansi(result.output)
    assert "Traceback" not in output
    assert "9" in output


def test_both_shared_name_obligations_report_changed_params(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions with two same-name obligations whose params each
    change, when running diff, then both changed param values are shown so
    neither obligation is silently dropped."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision_with_obligations(
            2,
            [
                obligation("data_masking", {"col": "ssn"}),
                obligation("data_masking", {"col": "dob"}),
            ],
        )
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision_with_obligations(
            3,
            [
                obligation("data_masking", {"col": "ssn_hash"}),
                obligation("data_masking", {"col": "dob_hash"}),
            ],
        )
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "ssn_hash" in output
    assert "dob_hash" in output


def test_added_obligation_renders_expanded_content(stub: tuple[Any, Any]) -> None:
    """Given two revisions where an obligation is added, when running diff, then
    its params and policyModelId render as nested field-lines under the added
    summary header, not just the name."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(revision_with_obligations(2, []))
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision_with_obligations(
            3, [obligation("data_masking", {"col": "ssn", "region": "eu"})]
        )
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "allowObligations: data_masking" in output
    assert "params.col" in output and "ssn" in output
    assert "region" in output and "eu" in output
    assert "policyModelId" in output


def test_removed_obligation_renders_expanded_content(stub: tuple[Any, Any]) -> None:
    """Given two revisions where an obligation is removed, when running diff,
    then its params render as nested remove field-lines under the removed
    summary header."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision_with_obligations(2, [obligation("data_masking", {"col": "ssn"})])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(revision_with_obligations(3, []))
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "allowObligations: data_masking" in output
    assert "params.col" in output and "ssn" in output


def test_added_obligations_render_each_param_shape(stub: tuple[Any, Any]) -> None:
    """Given two revisions adding a data_masking and an enforce_table_list
    obligation, when running diff, then the distinct param fields of each shape
    are rendered."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(revision_with_obligations(2, []))
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision_with_obligations(
            3,
            [
                obligation("data_masking", {"mask_fields": "ssn,dob"}),
                obligation("enforce_table_list", {"tables": "orders,users"}),
            ],
        )
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "params.mask_fields" in output and "ssn,dob" in output
    assert "params.tables" in output and "orders,users" in output


def test_added_deny_obligation_expands_like_allow(stub: tuple[Any, Any]) -> None:
    """Given two revisions where a denyObligations entry is added, when running
    diff, then its content expands identically to an allowObligations add."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision_with_obligations(2, [], deny=True)
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision_with_obligations(
            3, [obligation("data_masking", {"col": "ssn"})], deny=True
        )
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "denyObligations: data_masking" in output
    assert "params.col" in output and "ssn" in output


def test_unified_added_obligation_keeps_json_body_unchanged(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions where an obligation is added, when running diff with
    --format unified, then the obligation is rendered in the JSON body and the
    semantic dotted field-line style does not leak into the unified output."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(revision_with_obligations(2, []))
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision_with_obligations(3, [obligation("data_masking", {"col": "ssn"})])
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "policies", "diff", "10", "--format", "unified"]
    )
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "@@" in output
    assert '"name": "data_masking"' in output
    assert "allowObligations.data_masking" not in output
