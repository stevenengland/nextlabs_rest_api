from __future__ import annotations

import json
from typing import Any

import pytest
from mockito import when
from strip_ansi import strip_ansi

from nextlabs_sdk._cli._app import app

from tests.cli.policy_diff_helpers import (
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


def test_output_json_emits_structured_delta_overriding_format(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions differing in description, when running diff with the
    global --output json together with --format unified, then it emits the
    structured JSON delta and not the unified text render (json overrides
    format)."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision(2, description="allow read access")
    )
    result = runner.invoke(
        app,
        [
            *GLOBAL_OPTS,
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
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision(2, description="allow read access")
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "--output", "json", "policies", "diff", "10"]
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
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision(2, description="allow read access")
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "--output", "json", "policies", "diff", "10"]
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
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision_with_subjects(2, [component(5, "Engineers", version=1)])
    )
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision_with_subjects(3, [component(5, "Engineers", version=2)])
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "--output", "json", "policies", "diff", "10"]
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
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 2).thenReturn(revision_with_obligations(2, []))
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision_with_obligations(3, [obligation("data_masking", {"col": "ssn"})])
    )
    result = runner.invoke(
        app, [*GLOBAL_OPTS, "--output", "json", "policies", "diff", "10"]
    )
    assert result.exit_code == 0
    payload = json.loads(strip_ansi(result.output))
    added = next(change for change in payload["changes"] if change["kind"] == "add")
    assert added["new"]["name"] == "data_masking"
