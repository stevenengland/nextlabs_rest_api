from __future__ import annotations

from typing import Any

import pytest
from mockito import when

from nextlabs_sdk._cli._app import app

from tests.cli.policy_diff_helpers import (
    GLOBAL_OPTS,
    entry,
    make_stub,
    revision,
    runner,
)


@pytest.fixture
def stub() -> tuple[Any, Any]:
    return make_stub()


def test_exit_code_flag_exits_nonzero_when_differences_exist(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions that differ after noise filtering, when running diff
    with --exit-code, then the command exits non-zero."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision(3, description="allow write access")
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision(2, description="allow read access")
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10", "--exit-code"])
    assert result.exit_code != 0


def test_exit_code_flag_exits_zero_when_revisions_equivalent(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions that are equivalent after noise filtering, when
    running diff with --exit-code, then the command exits zero."""
    _, mock_policies = stub
    when(mock_policies).list_history(10).thenReturn([entry(2), entry(3)])
    when(mock_policies).get_revision(10, 3).thenReturn(
        revision(3, description="same text", deployment_time=200)
    )
    when(mock_policies).get_revision(10, 2).thenReturn(
        revision(2, description="same text", deployment_time=100)
    )
    result = runner.invoke(app, [*GLOBAL_OPTS, "policies", "diff", "10", "--exit-code"])
    assert result.exit_code == 0


def test_without_exit_code_flag_exits_zero_despite_differences(
    stub: tuple[Any, Any],
) -> None:
    """Given two revisions that differ after noise filtering, when running diff
    without --exit-code, then the command still exits zero."""
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
