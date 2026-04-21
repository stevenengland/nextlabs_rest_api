from __future__ import annotations

import pytest
from typer.testing import CliRunner

from nextlabs_sdk._cli import _auth_cmd
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cli._context import CliContext

runner = CliRunner()


def test_pdp_client_id_option_populates_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[CliContext] = []

    def _fake_pdp(cli_ctx: CliContext) -> None:
        seen.append(cli_ctx)

    monkeypatch.setattr(_auth_cmd, "_login_pdp", _fake_pdp)

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--pdp-client-id",
            "my-pdp-client",
            "--client-secret",
            "s3cret",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 0, result.output
    assert seen and seen[0].pdp_client_id == "my-pdp-client"


def test_pdp_client_id_env_var_populates_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[CliContext] = []
    monkeypatch.setenv("NEXTLABS_PDP_CLIENT_ID", "env-pdp-client")

    def _fake_pdp(cli_ctx: CliContext) -> None:
        seen.append(cli_ctx)

    monkeypatch.setattr(_auth_cmd, "_login_pdp", _fake_pdp)

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--client-secret",
            "s3cret",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 0, result.output
    assert seen and seen[0].pdp_client_id == "env-pdp-client"
