from __future__ import annotations

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
    revision: int, description: str = "d", deployment_time: int = 0
) -> PolicyRevision:
    return PolicyRevision(
        id=10,
        revision=revision,
        action_type="DE",
        policy_detail=Policy(
            id=82,
            name="P",
            status="DRAFT",
            effect_type="ALLOW",
            description=description,
            deployment_time=deployment_time,
        ),
    )


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
    when(mock_policies).list_history(10).thenReturn([_entry(2), _entry(3)])
    when(mock_policies).get_revision(10, 1).thenReturn(
        _revision(1, description="allow read access")
    )
    when(mock_policies).get_revision(10, 4).thenReturn(
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
