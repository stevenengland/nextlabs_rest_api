from __future__ import annotations

from typer.testing import CliRunner

from nextlabs_sdk._cli._app import app

runner = CliRunner()


def test_verbose_flag_appears_in_help():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "-v" in result.output
    assert "--verbose" in result.output
