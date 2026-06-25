from __future__ import annotations

import json
from typing import Any

import pytest
from mockito import mock, when
from strip_ansi import strip_ansi
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk.cloudaz import (
    CloudAzClient,
    Policy,
    PolicyHistoryEntry,
    PolicyRevision,
    PolicyService,
    Tag,
)

runner = CliRunner()

_GLOBAL_OPTS = (
    "--base-url",
    "https://example.com",
    "--username",
    "admin",
    "--password",
    "secret",
)


@pytest.fixture
def stub() -> tuple[Any, Any]:
    mock_client = mock(CloudAzClient)
    mock_policies = mock(PolicyService)
    mock_client.policies = mock_policies
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)
    return mock_client, mock_policies


def _entry(revision: int, action_type: str = "DE") -> PolicyHistoryEntry:
    return PolicyHistoryEntry(id=10, revision=revision, action_type=action_type)


def _revision(
    revision: int,
    description: str = "d",
    deployment_time: int = 0,
    effect_type: str = "ALLOW",
) -> PolicyRevision:
    return PolicyRevision(
        id=10,
        revision=revision,
        action_type="DE",
        policy_detail=Policy(
            id=82,
            name="P",
            status="DRAFT",
            effect_type=effect_type,
            description=description,
            deployment_time=deployment_time,
        ),
    )


def _component(component_id: int, name: str, version: int = 1) -> dict[str, Any]:
    return {"id": component_id, "name": name, "version": version, "subComponents": []}


def _revision_with_subjects(
    revision: int, components: list[dict[str, Any]]
) -> PolicyRevision:
    policy = Policy.model_validate(
        {
            "id": 82,
            "name": "P",
            "status": "DRAFT",
            "effectType": "ALLOW",
            "subjectComponents": [{"operator": "AND", "components": components}],
        }
    )
    return PolicyRevision(
        id=10, revision=revision, action_type="DE", policy_detail=policy
    )


def _revision_with_subject_groups(
    revision: int, groups: list[dict[str, Any]]
) -> PolicyRevision:
    policy = Policy.model_validate(
        {
            "id": 82,
            "name": "P",
            "status": "DRAFT",
            "effectType": "ALLOW",
            "subjectComponents": groups,
        }
    )
    return PolicyRevision(
        id=10, revision=revision, action_type="DE", policy_detail=policy
    )


def test_edited_component_renders_single_modified_entry(stub: tuple[Any, Any]) -> None:
    """Given two revisions where a subject component's version is bumped, when
    running diff, then it shows a single modified entry by name and id, not a
    remove-plus-add."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision_with_subjects(2, [_component(5, "Engineers", version=1)])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision_with_subjects(3, [_component(5, "Engineers", version=2)])
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "diff", "10"])
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
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision_with_subjects(2, [_component(5, "Engineers")])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision_with_subjects(3, [_component(6, "Operations")])
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "Engineers (id=5)" in output
    assert "Operations (id=6)" in output


def test_diff_default_renders_semantic_report(stub: tuple[Any, Any]) -> None:
    """Given two deployed revisions differing in description, when running diff
    with no flags, then it succeeds and shows the changed scalar."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision(2, description="allow read access")
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "write" in output


def test_diff_format_semantic_renders_semantic_report(stub: tuple[Any, Any]) -> None:
    """Given two deployed revisions differing in description, when running diff
    with --format semantic, then it renders the semantic report showing the
    changed scalar."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision(2, description="allow read access")
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "policies", "diff", "10", "--format", "semantic"]
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
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision(2, description="allow read access")
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "Policy: P (id=82)" in output
    assert "Comparing revisions 2 \u2192 3" in output
    assert output.index("Policy: P (id=82)") < output.index("description")


def test_diff_unified_shows_policy_row_and_git_revision_labels(
    stub: tuple[Any, Any],
) -> None:
    """Given two deployed revisions, when running diff with --format unified,
    then the output carries the policy identity row and the git revision labels
    derived from the compared revision numbers."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision(2, description="allow read access")
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "policies", "diff", "10", "--format", "unified"]
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
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision(2, description="allow read access")
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "policies", "diff", "10", "--format", "unified"]
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
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision(3, deployment_time=200)
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision(2, deployment_time=100)
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "diff", "10", "--show-all"])
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
        _revision(1, description="allow read access")
    )
    when(mock_policies).get_revision(24, 4).thenReturn(
        _revision(4, description="allow write access")
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "policies", "diff", "10", "--from", "1", "--to", "4"]
    )
    assert result.exit_code == 0
    assert "write" in strip_ansi(result.output)


def test_diff_too_few_revisions_exits_nonzero_without_traceback(
    stub: tuple[Any, Any],
) -> None:
    """Given a policy with only one deployed revision, when running diff, then
    it exits non-zero with a clear message and no traceback."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(3)])
    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "diff", "10"])
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
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "policies", "diff", "10", "--from", "2", "--to", "9"]
    )
    assert result.exit_code != 0
    output = strip_ansi(result.output)
    assert "Traceback" not in output
    assert "9" in output


def _obligation(name: str, params: dict[str, str]) -> dict[str, Any]:
    return {"id": None, "policyModelId": 0, "name": name, "params": params}


def _revision_with_obligations(
    revision: int, obligations: list[dict[str, Any]]
) -> PolicyRevision:
    policy = Policy.model_validate(
        {
            "id": 82,
            "name": "P",
            "status": "DRAFT",
            "effectType": "ALLOW",
            "allowObligations": obligations,
        }
    )
    return PolicyRevision(
        id=10, revision=revision, action_type="DE", policy_detail=policy
    )


def test_both_shared_name_obligations_report_changed_params(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions with two same-name obligations whose params each
    change, when running diff, then both changed param values are shown so
    neither obligation is silently dropped."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision_with_obligations(
            2,
            [
                _obligation("data_masking", {"col": "ssn"}),
                _obligation("data_masking", {"col": "dob"}),
            ],
        )
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision_with_obligations(
            3,
            [
                _obligation("data_masking", {"col": "ssn_hash"}),
                _obligation("data_masking", {"col": "dob_hash"}),
            ],
        )
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "ssn_hash" in output
    assert "dob_hash" in output


def test_output_json_emits_structured_delta_overriding_format(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions differing in description, when running diff with the
    global --output json together with --format unified, then it emits the
    structured JSON delta and not the unified text render (json overrides
    format)."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision(2, description="allow read access")
    )
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "--output",
            "json",
            "policies",
            "diff",
            "10",
            "--format",
            "unified",
        ],
    )
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "@@" not in output
    payload = json.loads(output)
    assert "changes" in payload


def test_output_json_delta_enumerates_path_kind_old_new(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions whose description changes, when running diff with the
    global --output json, then each change entry carries its path, kind, old
    value and new value."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision(2, description="allow read access")
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "--output", "json", "policies", "diff", "10"]
    )
    assert result.exit_code == 0
    payload = json.loads(strip_ansi(result.output))
    changes = payload["changes"]
    assert changes
    described = next(c for c in changes if c["path"] == ["description"])
    assert described["kind"] == "change"
    assert described["old"] == "allow read access"
    assert described["new"] == "allow write access"


def test_output_json_has_no_text_header(stub: tuple[Any, Any]) -> None:
    """Given two revisions, when running diff with --output json, then the
    structured delta is emitted with no human identity header text."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision(2, description="allow read access")
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "--output", "json", "policies", "diff", "10"]
    )
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "Policy:" not in output
    assert "Comparing revisions" not in output
    assert json.loads(output)["changes"]


def test_output_json_serializes_component_version_bump(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions where a subject component's version is bumped, when
    running diff with the global --output json, then the change entry's old and
    new carry JSON objects describing the component identity and version."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision_with_subjects(2, [_component(5, "Engineers", version=1)])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision_with_subjects(3, [_component(5, "Engineers", version=2)])
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "--output", "json", "policies", "diff", "10"]
    )
    assert result.exit_code == 0
    payload = json.loads(strip_ansi(result.output))
    component_change = next(
        change for change in payload["changes"] if change["kind"] == "change"
    )
    assert component_change["old"]["version"] == 1
    assert component_change["new"]["version"] == 2
    assert component_change["new"]["name"] == "Engineers"


def test_output_json_serializes_obligation_addition(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions where an obligation is added, when running diff with
    the global --output json, then the added change entry's new carries a JSON
    object identifying the obligation by name."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision_with_obligations(2, [])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision_with_obligations(3, [_obligation("data_masking", {"col": "ssn"})])
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "--output", "json", "policies", "diff", "10"]
    )
    assert result.exit_code == 0
    payload = json.loads(strip_ansi(result.output))
    added = next(change for change in payload["changes"] if change["kind"] == "add")
    assert added["new"]["name"] == "data_masking"


def test_exit_code_flag_exits_nonzero_when_differences_exist(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions that differ after noise filtering, when running diff
    with --exit-code, then the command exits non-zero."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision(2, description="allow read access")
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "policies", "diff", "10", "--exit-code"]
    )
    assert result.exit_code != 0


def test_exit_code_flag_exits_zero_when_revisions_equivalent(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions that are equivalent after noise filtering, when
    running diff with --exit-code, then the command exits zero."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision(3, description="same text", deployment_time=200)
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision(2, description="same text", deployment_time=100)
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "policies", "diff", "10", "--exit-code"]
    )
    assert result.exit_code == 0


def test_without_exit_code_flag_exits_zero_despite_differences(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions that differ after noise filtering, when running diff
    without --exit-code, then the command still exits zero."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision(2, description="allow read access")
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0


def test_scalar_effect_type_change_renders_old_and_new_lines(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions where effect_type changes from ALLOW to DENY, when
    running diff, then the output contains the old value on a '-' line and the
    new value on a '+' line."""
    # given
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision(2, effect_type="ALLOW")
    )
    when(mock_policies).get_revision(10, 3).thenReturn(_revision(3, effect_type="DENY"))
    # when
    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "diff", "10"])
    output = strip_ansi(result.output)
    # then
    assert result.exit_code == 0
    assert "- ALLOW" in output
    assert "+ DENY" in output


def _revision_with_tags(revision: int, tags: list[Tag]) -> PolicyRevision:
    return PolicyRevision(
        id=10,
        revision=revision,
        action_type="DE",
        policy_detail=Policy(
            id=82,
            name="P",
            status="DRAFT",
            effect_type="ALLOW",
            tags=tags,
        ),
    )


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
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision_with_tags(2, [Tag(id=1, key="old1", label="OLD1")])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision_with_tags(3, [Tag(id=2, key="adr6", label="ADR6")])
    )
    # when
    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "diff", "10"])
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
    when(mock_policies).list_history(82).thenReturn([_entry(2), _entry(3)])
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
        app, [*_GLOBAL_OPTS, "--output", "json", "policies", "diff", "82"]
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
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision(2, description="allow read access")
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision(3, description="allow write access")
    )
    # when
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "policies", "diff", "10", "--format", "unified"]
    )
    output = strip_ansi(result.output)
    # then
    assert result.exit_code == 0
    assert "@@" in output
    assert any(line.startswith("+") and "write" in line for line in output.splitlines())


def _grouped(operator: str, *components: dict[str, Any]) -> dict[str, Any]:
    return {"operator": operator, "components": list(components)}


def test_diff_reports_grouping_change_when_operator_flips(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions whose subject group operator flips with identical
    members, when running diff, then a grouping change block is shown rather
    than a membership change."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision_with_subject_groups(
            2, [_grouped("OR", _component(5, "Engineers"), _component(6, "Ops"))]
        )
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision_with_subject_groups(
            3, [_grouped("AND", _component(5, "Engineers"), _component(6, "Ops"))]
        )
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "diff", "10"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "grouping:" in output
    assert "was:  [OR : Engineers, Ops]" in output
    assert "now:  [AND: Engineers, Ops]" in output


def test_diff_grouping_change_flips_exit_code(stub: tuple[Any, Any]) -> None:
    """Given a subject group operator flip, when running diff with
    --exit-code, then the command exits non-zero."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision_with_subject_groups(2, [_grouped("OR", _component(5, "Engineers"))])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision_with_subject_groups(3, [_grouped("AND", _component(5, "Engineers"))])
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "policies", "diff", "10", "--exit-code"]
    )
    assert result.exit_code == 1


def test_diff_grouping_change_appears_in_unified_format(
    stub: tuple[Any, Any],
) -> None:
    """Given a subject group operator flip, when running diff with --format
    unified, then the operator drift surfaces in the unified output."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision_with_subject_groups(2, [_grouped("OR", _component(5, "Engineers"))])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision_with_subject_groups(3, [_grouped("AND", _component(5, "Engineers"))])
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "policies", "diff", "10", "--format", "unified"]
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
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision_with_subject_groups(2, [_grouped("OR", _component(5, "Engineers"))])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision_with_subject_groups(3, [_grouped("AND", _component(5, "Engineers"))])
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "policies", "diff", "10", "--format", "unified"]
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
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        _revision_with_subject_groups(2, [_grouped("OR", _component(5, "Engineers"))])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        _revision_with_subject_groups(3, [_grouped("or ", _component(5, "Engineers"))])
    )
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "diff", "10", "--format", "unified", "--exit-code"],
    )
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "operator" not in output
    assert "grouping" not in output


def _cross_revision(
    policy_id: int,
    name: str,
    revision: int,
    description: str = "d",
    components: list[dict[str, Any]] | None = None,
) -> PolicyRevision:
    payload: dict[str, Any] = {
        "id": policy_id,
        "name": name,
        "status": "DRAFT",
        "effectType": "ALLOW",
        "description": description,
    }
    if components is not None:
        payload["subjectComponents"] = [{"operator": "AND", "components": components}]
    return PolicyRevision(
        id=policy_id * 10,
        revision=revision,
        action_type="DE",
        policy_detail=Policy.model_validate(payload),
    )


def test_diff_two_policies_compares_latest_revisions_semantic(
    stub: tuple[Any, Any],
) -> None:
    """Given two distinct policy ids each with deployed revisions, when running
    diff with two positional ids, then it compares each policy's latest revision
    and renders a semantic diff of their bodies."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(1), _entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=5, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _cross_revision(10, "Alpha", 2, description="read")
    )
    when(mock_policies).get_revision(200, 5).thenReturn(
        _cross_revision(20, "Beta", 5, description="write")
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "diff", "10", "20"])
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
    when(mock_policies).list_history(10).thenReturn([_entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _cross_revision(10, "Alpha", 2, description="same")
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        _cross_revision(20, "Beta", 2, description="same")
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "diff", "10", "20"])
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
    when(mock_policies).list_history(10).thenReturn([_entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=5, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _cross_revision(10, "Alpha", 2, description="read")
    )
    when(mock_policies).get_revision(200, 5).thenReturn(
        _cross_revision(20, "Beta", 5, description="write")
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "diff", "10", "20"])
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
    when(mock_policies).list_history(10).thenReturn([_entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _cross_revision(10, "Alpha", 2, components=[_component(5, "Engineers")])
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        _cross_revision(20, "Beta", 2, components=[_component(5, "Managers")])
    )
    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "diff", "10", "20"])
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
        _cross_revision(10, "Alpha", 1, description="read")
    )
    when(mock_policies).get_revision(200, 7).thenReturn(
        _cross_revision(20, "Beta", 7, description="write")
    )
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "diff", "10", "20", "--from", "1", "--to", "7"],
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
    when(mock_policies).list_history(10).thenReturn([_entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _cross_revision(10, "Alpha", 2, description="same")
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        _cross_revision(20, "Beta", 2, description="same")
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "policies", "diff", "10", "20", "--exit-code"]
    )
    assert result.exit_code == 0


def test_diff_cross_policy_exit_code_nonzero_when_body_differs(
    stub: tuple[Any, Any],
) -> None:
    """Given two policies whose bodies differ, when running cross-policy diff
    with --exit-code, then it exits non-zero."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([_entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _cross_revision(10, "Alpha", 2, description="read")
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        _cross_revision(20, "Beta", 2, description="write")
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "policies", "diff", "10", "20", "--exit-code"]
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
    when(mock_policies).list_history(10).thenReturn([_entry(2)])
    when(mock_policies).list_history(20).thenReturn(
        [PolicyHistoryEntry(id=200, revision=2, action_type="DE")]
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        _cross_revision(10, "Alpha", 2, description="read")
    )
    when(mock_policies).get_revision(200, 2).thenReturn(
        _cross_revision(20, "Beta", 2, description="write")
    )
    result = runner.invoke(
        app, [*_GLOBAL_OPTS, "policies", "diff", "10", "20", "--format", "unified"]
    )
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "A: Alpha (id=10)" in output
    assert "B: Beta (id=20)" in output
    diff_lines = [line for line in output.splitlines() if line.startswith(("+", "-"))]
    assert not any('"name"' in line or '"id"' in line for line in diff_lines)
    assert any("write" in line and line.startswith("+") for line in diff_lines)
