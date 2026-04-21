from __future__ import annotations

from pathlib import Path
from typing import cast

import httpx
import pytest
from mockito import ANY, mock, when
from typer.testing import CliRunner

from nextlabs_sdk._auth._active_account._active_account_store import (
    ActiveAccountStore,
)
from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache
from nextlabs_sdk._cli import _auth_cmd, _client_factory
from nextlabs_sdk._cli._account_preferences_store import AccountPreferencesStore
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


# ─────────────────────────── Task 5: PDP login ───────────────────────────


class _TokenResp:
    status_code = 200
    text = ""

    def __init__(self, body: dict[str, object]) -> None:
        self._body = body

    def json(self) -> dict[str, object]:
        return self._body


class _ErrResp:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


def test_login_pdp_pdp_flavor_persists_all(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    resp = _TokenResp(
        {"access_token": "AT", "expires_in": 3600, "token_type": "bearer"},
    )
    when(httpx).post(
        "https://pdp.example/dpc/oauth",
        data=ANY,
        headers=ANY,
        timeout=ANY,
        verify=ANY,
    ).thenReturn(resp)

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--client-id",
            "ccid",
            "--client-secret",
            "S3cret",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 0, result.output

    cache = FileTokenCache(path=tmp_path / "tokens.json")
    entry = cache.load("https://pdp.example||ccid|pdp")
    assert entry is not None
    assert entry.access_token == "AT"
    assert entry.client_secret == "S3cret"

    prefs = AccountPreferencesStore(
        path=tmp_path / "account_prefs.json",
    ).load("https://pdp.example||ccid|pdp")
    assert prefs is not None
    assert prefs.pdp_url == "https://pdp.example"
    assert prefs.pdp_auth_source == "pdp"

    active = ActiveAccountStore(path=tmp_path / "active_account.json").load()
    assert active is not None
    assert active.kind == "pdp"
    assert active.base_url == "https://pdp.example"
    assert active.username == ""


def test_login_pdp_cloudaz_flavor_requires_base_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--client-id",
            "cc",
            "--client-secret",
            "S",
            "--pdp-auth",
            "cloudaz",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code != 0
    assert "base-url" in result.output.lower()


def test_login_pdp_token_error_surfaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    when(httpx).post(
        ANY,
        data=ANY,
        headers=ANY,
        timeout=ANY,
        verify=ANY,
    ).thenReturn(_ErrResp(status_code=401, text="bad creds"))

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--client-id",
            "cc",
            "--client-secret",
            "bad",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 1
    assert (
        "authentication failed" in result.output.lower()
        or "token acquisition" in result.output.lower()
    )
