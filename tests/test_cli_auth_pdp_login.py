from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _auth_cmd, _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._operators import OperatorService

runner = CliRunner()


def _mock_cloudaz_client() -> CloudAzClient:
    client = mock(CloudAzClient)
    ops = mock(OperatorService)
    client.operators = ops
    when(ops).list_types().thenReturn([])
    when(client).authenticate().thenReturn(None)
    return cast(CloudAzClient, client)


def _isolate_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXTLABS_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)


def _capture_factory(monkeypatch: pytest.MonkeyPatch) -> list[CliContext]:
    captured: list[CliContext] = []

    def _fake(ctx: CliContext) -> CloudAzClient:
        captured.append(ctx)
        return _mock_cloudaz_client()

    monkeypatch.setattr(_client_factory, "make_cloudaz_client", _fake)
    return captured


def test_login_type_cloudaz_keeps_existing_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    captured = _capture_factory(monkeypatch)

    result = runner.invoke(
        app,
        [
            "--base-url",
            "https://example.com",
            "--username",
            "admin",
            "--password",
            "secret",
            "auth",
            "login",
            "--type",
            "cloudaz",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured and captured[0].base_url == "https://example.com"


def test_login_without_type_in_non_tty_defaults_to_cloudaz(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    _capture_factory(monkeypatch)

    result = runner.invoke(
        app,
        [
            "--base-url",
            "https://example.com",
            "--username",
            "admin",
            "--password",
            "secret",
            "auth",
            "login",
        ],
    )

    assert result.exit_code == 0, result.output


def test_login_type_pdp_reaches_branch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    called: list[bool] = []

    def _fake_pdp(cli_ctx: CliContext) -> None:
        called.append(True)

    monkeypatch.setattr(_auth_cmd, "_login_pdp", _fake_pdp)

    result = runner.invoke(app, ["auth", "login", "--type", "pdp"])

    assert called == [True]
    assert result.exit_code == 0, result.output


def test_login_type_invalid_raises_bad_parameter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    _capture_factory(monkeypatch)

    result = runner.invoke(
        app,
        [
            "--base-url",
            "https://example.com",
            "--username",
            "admin",
            "--password",
            "secret",
            "auth",
            "login",
            "--type",
            "bogus",
        ],
    )

    assert result.exit_code != 0
    assert "type" in result.output.lower()
