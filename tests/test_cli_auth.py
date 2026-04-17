from __future__ import annotations

from typing import cast

import pytest
from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._operators import OperatorService
from nextlabs_sdk.exceptions import AuthenticationError

runner = CliRunner()

_GLOBAL_OPTS = (
    "--base-url",
    "https://example.com",
    "--username",
    "admin",
    "--password",
    "secret",
)


def _mock_cloudaz_client() -> CloudAzClient:
    mock_client = mock(CloudAzClient)
    mock_ops = mock(OperatorService)
    mock_client.operators = mock_ops
    when(mock_ops).list_types().thenReturn(["STRING", "NUMBER"])
    return cast(CloudAzClient, mock_client)


def test_auth_test_success() -> None:
    when(_client_factory).make_cloudaz_client(...).thenReturn(_mock_cloudaz_client())

    result = runner.invoke(app, [*_GLOBAL_OPTS, "auth", "test"])

    assert result.exit_code == 0
    assert "successful" in result.output.lower()


def test_auth_test_failure() -> None:
    when(_client_factory).make_cloudaz_client(...).thenRaise(
        AuthenticationError(message="bad creds"),
    )

    result = runner.invoke(app, [*_GLOBAL_OPTS, "auth", "test"])

    assert result.exit_code == 1
    assert "Authentication failed" in result.output


def test_auth_test_missing_credentials() -> None:
    result = runner.invoke(app, ["--base-url", "https://x.com", "auth", "test"])

    assert result.exit_code == 1
    assert "username" in result.output.lower()


# ─────────────────────────── login prompting ─────────────────────────────


def _isolate_cache(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEXTLABS_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)


def _capture_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> list[CliContext]:
    captured: list[CliContext] = []

    def _fake(ctx: CliContext) -> CloudAzClient:
        captured.append(ctx)
        return _mock_cloudaz_client()

    monkeypatch.setattr(_client_factory, "make_cloudaz_client", _fake)
    return captured


def test_login_prompts_for_password_when_missing(
    tmp_path: object,
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
            "auth",
            "login",
        ],
        input="s3cret\n",
    )

    assert result.exit_code == 0, result.output
    assert "Login successful" in result.output
    assert "s3cret" not in result.output  # hidden
    assert captured and captured[0].password == "s3cret"
    assert captured[0].base_url == "https://example.com"
    assert captured[0].username == "admin"


def test_login_prompts_for_everything_when_no_cache_and_no_flags(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    captured = _capture_factory(monkeypatch)

    result = runner.invoke(
        app,
        ["auth", "login"],
        input="https://example.com\nadmin\ns3cret\n",
    )

    assert result.exit_code == 0, result.output
    assert captured[0].base_url == "https://example.com"
    assert captured[0].username == "admin"
    assert captured[0].password == "s3cret"


def _seed_cache(tmp_path: object, *keys: str) -> None:
    from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
    from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache

    cache = FileTokenCache(path=f"{tmp_path}/tokens.json")
    tok = CachedToken(
        access_token="id",
        refresh_token="rt",
        expires_at=1000.0,
        token_type="bearer",
        scope=None,
    )
    for key in keys:
        cache.save(key, tok)


def test_login_shows_menu_when_cache_has_entries_and_flags_missing(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    _seed_cache(
        tmp_path,
        "https://alpha.example.com/cas/oidc/accessToken|alice|ControlCenterOIDCClient",
        "https://beta.example.com/cas/oidc/accessToken|bob|ControlCenterOIDCClient",
    )
    captured = _capture_factory(monkeypatch)

    # Pick entry 2 (bob @ beta), then enter password.
    result = runner.invoke(app, ["auth", "login"], input="2\ns3cret\n")

    assert result.exit_code == 0, result.output
    assert "alice" in result.output
    assert "bob" in result.output
    assert captured[0].base_url == "https://beta.example.com"
    assert captured[0].username == "bob"
    assert captured[0].password == "s3cret"


def test_login_menu_add_new_prompts_for_url_and_username(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    _seed_cache(
        tmp_path,
        "https://alpha.example.com/cas/oidc/accessToken|alice|ControlCenterOIDCClient",
    )
    captured = _capture_factory(monkeypatch)

    # Pick "Add new" (option 2), then enter url, username, password.
    result = runner.invoke(
        app,
        ["auth", "login"],
        input="2\nhttps://new.example.com\ncarol\np4ss\n",
    )

    assert result.exit_code == 0, result.output
    assert captured[0].base_url == "https://new.example.com"
    assert captured[0].username == "carol"
    assert captured[0].password == "p4ss"


def test_login_skips_menu_when_base_and_username_supplied(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    _seed_cache(
        tmp_path,
        "https://alpha.example.com/cas/oidc/accessToken|alice|ControlCenterOIDCClient",
    )
    captured = _capture_factory(monkeypatch)

    result = runner.invoke(
        app,
        [
            "--base-url",
            "https://beta.example.com",
            "--username",
            "bob",
            "auth",
            "login",
        ],
        input="s3cret\n",
    )

    assert result.exit_code == 0, result.output
    assert "alice" not in result.output  # menu not shown
    assert captured[0].base_url == "https://beta.example.com"
    assert captured[0].username == "bob"


def test_login_menu_selection_does_not_override_explicit_username(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    _seed_cache(
        tmp_path,
        "https://alpha.example.com/cas/oidc/accessToken|alice|ControlCenterOIDCClient",
    )
    captured = _capture_factory(monkeypatch)

    # Username is explicit ("carol"), base_url missing — menu is shown to fill URL.
    result = runner.invoke(
        app,
        ["--username", "carol", "auth", "login"],
        input="1\ns3cret\n",
    )

    assert result.exit_code == 0, result.output
    assert captured[0].base_url == "https://alpha.example.com"
    assert captured[0].username == "carol"  # explicit flag wins
