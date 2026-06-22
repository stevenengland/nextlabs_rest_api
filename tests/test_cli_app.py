from __future__ import annotations

import pytest
from typer.testing import CliRunner

from nextlabs_sdk._cli._app import app

runner = CliRunner()

_GROUPS = (
    "activity-logs",
    "audit-logs",
    "auth",
    "component-types",
    "components",
    "dashboard",
    "operators",
    "pdp",
    "policies",
    "reporter-audit-logs",
    "reports",
    "system-config",
    "tags",
)


def test_app_shows_help():
    # Given the root app
    # When invoked with --help
    result = runner.invoke(app, ["--help"])
    # Then it prints usage and exits zero
    assert result.exit_code == 0
    assert "nextlabs" in result.output.lower() or "Usage" in result.output


def test_app_no_args_shows_help():
    # Given the root app
    # When invoked with no arguments
    result = runner.invoke(app, [])
    # Then it prints help and exits two (no_args_is_help)
    assert result.exit_code == 2
    assert "Usage" in result.output


@pytest.mark.parametrize("group", _GROUPS)
def test_group_without_subcommand_shows_help(group: str):
    # Given a top-level command group
    # When invoked without a subcommand
    result = runner.invoke(app, [group])
    # Then it prints help (not a "Missing command" error) and exits two
    assert result.exit_code == 2
    assert "Usage" in result.output
    assert "Missing command" not in result.output
