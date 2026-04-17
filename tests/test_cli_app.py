from __future__ import annotations

from typer.testing import CliRunner

from nextlabs_sdk._cli._app import app

runner = CliRunner()


def test_app_shows_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "nextlabs" in result.output.lower() or "Usage" in result.output


def test_app_no_args_shows_help():
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Usage" in result.output
