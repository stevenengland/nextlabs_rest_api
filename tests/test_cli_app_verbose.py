from __future__ import annotations

from strip_ansi import strip_ansi
from typer.testing import CliRunner

from nextlabs_sdk._cli._app import app

runner = CliRunner()


def test_verbose_flag_appears_in_help():
    result = runner.invoke(app, ["--help"])
    output = strip_ansi(result.output)

    assert result.exit_code == 0
    assert "-v" in output
    assert "--verbose" in output


def test_help_mentions_vvv_and_body_limit_env(monkeypatch):
    monkeypatch.setenv("COLUMNS", "240")
    result = runner.invoke(app, ["--help"], terminal_width=240)
    output = strip_ansi(result.output)

    assert result.exit_code == 0
    assert "-vvv" in output
    assert "NEXTLABS_LOG_BODY_LIMIT" in output
