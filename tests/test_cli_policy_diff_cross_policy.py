from __future__ import annotations

import json
from typing import Any

import pytest
from mockito import when
from strip_ansi import strip_ansi

from nextlabs_sdk._cli._app import app
from nextlabs_sdk.cloudaz import PolicyHistoryEntry

from tests._policy_diff_helpers import (
    GLOBAL_OPTS,
    component,
    cross_revision,
    entry,
    make_stub,
    runner,
)


@pytest.fixture
def stub() -> tuple[Any, Any]:
    return make_stub()


def test_diff_two_policies_compares_latest_revisions_semantic(
    stub: tuple[Any, Any],
) -> None:
    """Given two distinct policy ids each with deployed revisions, when running
    diff with two positional ids, then it compares each policy's latest revision
    and renders a semantic diff of their bodies."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(1), entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=5, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        cross_revision(10, "Alpha", 2, description="read")
    )
    when(mock_policies).get_revision(200, 5).thenReturn(
        cross_revision(20, "Beta", 5, description="write")
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10", "20"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "description" in output
    assert "read" in output and "write" in output


def test_diff_cross_policy_strips_top_level_identity_fields(
    stub: tuple[Any, Any],
) -> None:
    """Given two policies that differ only in top-level identity fields, when
    running cross-policy diff, then those identity fields never appear as
    changes."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        cross_revision(10, "Alpha", 2, description="same")
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        cross_revision(20, "Beta", 2, description="same")
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10", "20"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    change_lines = [
        line
        for line in output.splitlines()
        if line.lstrip().startswith(("~", "+", "-"))
    ]
    assert not any("name" in line or "id" in line for line in change_lines)


def test_diff_cross_policy_header_shows_both_identities(
    stub: tuple[Any, Any],
) -> None:
    """Given two distinct policies, when running cross-policy diff, then the
    header shows both policy identities (name and id for each side)."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=5, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        cross_revision(10, "Alpha", 2, description="read")
    )
    when(mock_policies).get_revision(200, 5).thenReturn(
        cross_revision(20, "Beta", 5, description="write")
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10", "20"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "Alpha (id=10)" in output
    assert "Beta (id=20)" in output


def test_diff_cross_policy_nested_difference_surfaces(
    stub: tuple[Any, Any],
) -> None:
    """Given two policies whose only difference is a nested component name, when
    running cross-policy diff, then the nested difference still surfaces."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        cross_revision(10, "Alpha", 2, components=[component(5, "Engineers")])
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        cross_revision(20, "Beta", 2, components=[component(5, "Managers")])
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10", "20"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "Engineers" in output or "Managers" in output


def test_diff_cross_policy_from_to_select_each_side_revision(
    stub: tuple[Any, Any],
) -> None:
    """Given two policies, when running cross-policy diff with --from and --to,
    then --from selects policy A's revision and --to selects policy B's."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn(
        [PolicyHistoryEntry(id=100, revision=1, action_type="DR")]
    )
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=7, action_type="DR")]
    )
    when(mock_policies).get_revision(100, 1).thenReturn(
        cross_revision(10, "Alpha", 1, description="read")
    )
    when(mock_policies).get_revision(200, 7).thenReturn(
        cross_revision(20, "Beta", 7, description="write")
    )
    result = runner.invoke(
        app,
        [*GLOBAL_OPTS, "policies", "diff", "10", "20", "--from", "1", "--to", "7"],
    )
    assert result.exit_code == 0
    assert "write" in strip_ansi(result.output)


def test_diff_cross_policy_exit_code_nonzero_on_post_strip_difference(
    stub: tuple[Any, Any],
) -> None:
    """Given two policies that differ only in identity fields, when running
    cross-policy diff with --exit-code, then it exits zero because the only
    differences were stripped; a genuine body difference exits non-zero."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        cross_revision(10, "Alpha", 2, description="same")
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        cross_revision(20, "Beta", 2, description="same")
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "policies", "diff", "10", "20", "--exit-code"]
    )
    assert result.exit_code == 0


def test_diff_cross_policy_exit_code_nonzero_when_body_differs(
    stub: tuple[Any, Any],
) -> None:
    """Given two policies whose bodies differ, when running cross-policy diff
    with --exit-code, then it exits non-zero."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        cross_revision(10, "Alpha", 2, description="read")
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        cross_revision(20, "Beta", 2, description="write")
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "policies", "diff", "10", "20", "--exit-code"]
    )
    assert result.exit_code == 1


def test_diff_cross_policy_unified_header_and_strips_identity(
    stub: tuple[Any, Any],
) -> None:
    """Given two policies differing in identity fields and description, when
    running cross-policy diff with --format unified, then the header names both
    policies and the identity fields never appear as unified diff lines while
    the body difference does."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        cross_revision(10, "Alpha", 2, description="read")
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        cross_revision(20, "Beta", 2, description="write")
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "policies", "diff", "10", "20", "--format", "unified"]
    )
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "A: Alpha (id=10)" in output
    assert "B: Beta (id=20)" in output
    diff_lines = [line for line in output.splitlines() if line.startswith(("+", "-"))]
    assert not any('"name"' in line or '"id"' in line for line in diff_lines)
    assert any("write" in line and line.startswith("+") for line in diff_lines)


def test_diff_cross_policy_show_all_reveals_identity_fields(
    stub: tuple[Any, Any],
) -> None:
    """Given two policies differing only in top-level identity fields, when
    running cross-policy diff with --show-all, then the otherwise-stripped
    identity fields surface as ordinary changes."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        cross_revision(10, "Alpha", 2, description="same")
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        cross_revision(20, "Beta", 2, description="same")
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "policies", "diff", "10", "20", "--show-all"]
    )
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    change_lines = [
        line
        for line in output.splitlines()
        if line.lstrip().startswith(("~", "+", "-"))
    ]
    assert any("name" in line for line in change_lines)


def test_diff_cross_policy_show_all_unified_reveals_identity_fields(
    stub: tuple[Any, Any],
) -> None:
    """Given two policies differing only in top-level identity fields, when
    running cross-policy diff with --show-all --format unified, then the
    identity fields appear in the unified diff body."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        cross_revision(10, "Alpha", 2, description="same")
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        cross_revision(20, "Beta", 2, description="same")
    )
    result = runner.invoke(
        app,
        [
            *GLOBAL_OPTS,
            "policies",
            "diff",
            "10",
            "20",
            "--show-all",
            "--format",
            "unified",
        ],
    )
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    diff_lines = [line for line in output.splitlines() if line.startswith(("+", "-"))]
    assert any('"name"' in line for line in diff_lines)


def test_diff_cross_policy_semantic_header_notes_identity_ignored(
    stub: tuple[Any, Any],
) -> None:
    """Given two distinct policies, when running cross-policy diff without
    --show-all in semantic format, then the header notes that identity fields
    are ignored."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        cross_revision(10, "Alpha", 2, description="read")
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        cross_revision(20, "Beta", 2, description="write")
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10", "20"])
    assert result.exit_code == 0
    assert "identity fields ignored" in strip_ansi(result.output)


def test_diff_cross_policy_semantic_show_all_omits_identity_note(
    stub: tuple[Any, Any],
) -> None:
    """Given two distinct policies, when running cross-policy diff with
    --show-all in semantic format, then the header does not claim identity
    fields are ignored, because --show-all reveals them."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        cross_revision(10, "Alpha", 2, description="read")
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        cross_revision(20, "Beta", 2, description="write")
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "policies", "diff", "10", "20", "--show-all"]
    )
    assert result.exit_code == 0
    assert "identity fields ignored" not in strip_ansi(result.output)


def test_diff_cross_policy_unified_show_all_omits_identity_note(
    stub: tuple[Any, Any],
) -> None:
    """Given two distinct policies, when running cross-policy diff with
    --show-all --format unified, then the header does not claim identity fields
    are ignored, because --show-all reveals them in the body."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        cross_revision(10, "Alpha", 2, description="read")
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        cross_revision(20, "Beta", 2, description="write")
    )
    result = runner.invoke(
        app,
        [
            *GLOBAL_OPTS,
            "policies",
            "diff",
            "10",
            "20",
            "--show-all",
            "--format",
            "unified",
        ],
    )
    assert result.exit_code == 0
    assert "identity fields ignored" not in strip_ansi(result.output)


def test_diff_cross_policy_output_json_strips_identity_fields(
    stub: tuple[Any, Any],
) -> None:
    """Given two distinct policies differing in top-level identity and in a
    body field, when running cross-policy diff with the global --output json,
    then the structured delta surfaces the body change but never the stripped
    top-level identity fields."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        cross_revision(10, "Alpha", 2, description="read")
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        cross_revision(20, "Beta", 2, description="write")
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "--output", "json", "policies", "diff", "10", "20"]
    )
    assert result.exit_code == 0
    payload = json.loads(strip_ansi(result.output))
    top_level_paths = {
        change["path"][0] for change in payload["changes"] if change["path"]
    }
    assert "name" not in top_level_paths
    assert "id" not in top_level_paths
    assert "description" in top_level_paths
