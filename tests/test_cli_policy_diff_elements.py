from __future__ import annotations

import json
from typing import Any

import pytest
from mockito import when
from strip_ansi import strip_ansi

from nextlabs_sdk._cli._app import app
from nextlabs_sdk.cloudaz import Policy, PolicyRevision, Tag

from tests._policy_diff_helpers import (
    GLOBAL_OPTS,
    component,
    entry,
    grouped,
    make_stub,
    revision,
    revision_with_subject_groups,
    revision_with_tags,
    runner,
)


@pytest.fixture
def stub() -> tuple[Any, Any]:
    return make_stub()


def test_scalar_effect_type_change_renders_old_and_new_lines(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions where effect_type changes from ALLOW to DENY, when
    running diff, then the output contains the old value on a '-' line and the
    new value on a '+' line."""
    # given
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(revision(2, effect_type="ALLOW"))
    when(mock_policies).get_revision(10, 3).thenReturn(revision(3, effect_type="DENY"))
    # when
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10"])
    output = strip_ansi(result.output)
    # then
    assert result.exit_code == 0
    assert "- ALLOW" in output
    assert "+ DENY" in output


def test_tag_add_and_remove_render_as_glyph_lines(stub: tuple[Any, Any]) -> None:
    """Given two revisions where one tag is added and another is removed, when
    running diff, then a '+' line shows the added tag and a '-' line shows the
    removed tag, both in 'key (LABEL)' format.

    Given two revisions differing in tags,
    when running the diff command,
    then the output contains a '+' line for the added tag and a '-' line for the removed tag.
    """
    # given
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision_with_tags(2, [Tag(id=1, key="old1", label="OLD1")])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision_with_tags(3, [Tag(id=2, key="adr6", label="ADR6")])
    )
    # when
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10"])
    output = strip_ansi(result.output)
    # then
    assert result.exit_code == 0
    assert "+ adr6 (ADR6)" in output
    assert "- old1 (OLD1)" in output


def test_diff_json_emits_per_element_tag_changes(stub: tuple[Any, Any]) -> None:
    """Given two revisions whose tags differ by one added tag, when running diff
    with --output json, then the changes array contains a per-element tag entry
    with path[0] == 'tags' and new carrying key and label."""
    # given
    _, mock_policies = stub
    when(mock_policies).list_history(82).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        PolicyRevision(
            id=10,
            revision=2,
            action_type="DE",
            policy_detail=Policy(
                id=82,
                name="P",
                status="DRAFT",
                effect_type="ALLOW",
                tags=[],
            ),
        )
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        PolicyRevision(
            id=10,
            revision=3,
            action_type="DE",
            policy_detail=Policy(
                id=82,
                name="P",
                status="DRAFT",
                effect_type="ALLOW",
                tags=[Tag(key="adr6", label="ADR6")],
            ),
        )
    )
    # when
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "--output", "json", "policies", "diff", "82"]
    )
    # then
    assert result.exit_code == 0
    payload = json.loads(strip_ansi(result.output))
    tag_entries = [
        c for c in payload["changes"] if c["path"] and c["path"][0] == "tags"
    ]
    assert tag_entries
    assert tag_entries[0]["new"] == {"key": "adr6", "label": "ADR6"}


def test_diff_unified_format_unaffected_by_tag_changes(stub: tuple[Any, Any]) -> None:
    """Given two revisions differing by a tag change, when running diff with
    --format unified, then the output is a git-style unified diff unaffected
    by the semantic-path work.

    Given two revisions where a tag is changed,
    when running the diff command with --format unified,
    then the output contains standard unified-diff markers (@@) and the changed
    value appears on a '+' line.
    """
    # given
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision(2, description="allow read access")
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision(3, description="allow write access")
    )
    # when
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "policies", "diff", "10", "--format", "unified"]
    )
    output = strip_ansi(result.output)
    # then
    assert result.exit_code == 0
    assert "@@" in output
    assert any(line.startswith("+") and "write" in line for line in output.splitlines())


def test_diff_reports_grouping_change_when_operator_flips(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions whose subject group operator flips with identical
    members, when running diff, then a grouping change block is shown rather
    than a membership change."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision_with_subject_groups(
            2, [grouped("OR", component(5, "Engineers"), component(6, "Ops"))]
        )
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision_with_subject_groups(
            3, [grouped("AND", component(5, "Engineers"), component(6, "Ops"))]
        )
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "grouping:" in output
    assert "was:  [OR : Engineers, Ops]" in output
    assert "now:  [AND: Engineers, Ops]" in output


def test_diff_grouping_change_flips_exit_code(stub: tuple[Any, Any]) -> None:
    """Given a subject group operator flip, when running diff with
    --exit-code, then the command exits non-zero."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision_with_subject_groups(2, [grouped("OR", component(5, "Engineers"))])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision_with_subject_groups(3, [grouped("AND", component(5, "Engineers"))])
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10", "--exit-code"])
    assert result.exit_code == 1


def test_diff_grouping_change_appears_in_unified_format(
    stub: tuple[Any, Any],
) -> None:
    """Given a subject group operator flip, when running diff with --format
    unified, then the operator drift surfaces in the unified output."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision_with_subject_groups(2, [grouped("OR", component(5, "Engineers"))])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision_with_subject_groups(3, [grouped("AND", component(5, "Engineers"))])
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "policies", "diff", "10", "--format", "unified"]
    )
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert any(line.startswith("-") and "OR" in line for line in output.splitlines())
    assert any(line.startswith("+") and "AND" in line for line in output.splitlines())


def test_diff_unified_renders_structured_grouping_block(
    stub: tuple[Any, Any],
) -> None:
    """Given a subject group operator flip, when running diff with --format
    unified, then the grouping change renders as a structured block keyed by
    the slot's grouping path rather than as a raw operator JSON line."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision_with_subject_groups(2, [grouped("OR", component(5, "Engineers"))])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision_with_subject_groups(3, [grouped("AND", component(5, "Engineers"))])
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "policies", "diff", "10", "--format", "unified"]
    )
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "subjectComponents.grouping" in output
    assert any(line.startswith("-") and "[OR" in line for line in output.splitlines())
    assert any(line.startswith("+") and "[AND" in line for line in output.splitlines())
    assert '"operator"' not in output


def test_diff_unified_ignores_cosmetic_operator_change_matching_semantic(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions whose group operator differs only in case and
    trailing whitespace (semantically identical), when running diff with
    --format unified, then no operator change surfaces, matching the semantic
    format which reports no change and a zero exit code."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision_with_subject_groups(2, [grouped("OR", component(5, "Engineers"))])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision_with_subject_groups(3, [grouped("or ", component(5, "Engineers"))])
    )
    result = runner.invoke(
        app,
        [*GLOBAL_OPTS, "policies", "diff", "10", "--format", "unified", "--exit-code"],
    )
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "operator" not in output
    assert "grouping" not in output
