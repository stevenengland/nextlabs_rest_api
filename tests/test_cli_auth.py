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
    when(mock_client).authenticate().thenReturn(None)
    return cast(CloudAzClient, mock_client)


def test_auth_test_success():
    when(_client_factory).make_cloudaz_client(...).thenReturn(_mock_cloudaz_client())

    result = runner.invoke(app, [*_GLOBAL_OPTS, "auth", "test"])

    assert result.exit_code == 0
    assert "successful" in result.output.lower()


def test_auth_test_failure():
    when(_client_factory).make_cloudaz_client(...).thenRaise(
        AuthenticationError(message="bad creds"),
    )

    result = runner.invoke(app, [*_GLOBAL_OPTS, "auth", "test"])

    assert result.exit_code == 1
    assert "Authentication failed" in result.output


def test_auth_test_missing_credentials():
    result = runner.invoke(app, ["--base-url", "https://x.com", "auth", "test"])

    assert result.exit_code == 1
    assert "username" in result.output.lower()


def _isolate_cache(tmp_path: object, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NEXTLABS_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)


def _capture_factory(monkeypatch: pytest.MonkeyPatch) -> list[CliContext]:
    captured: list[CliContext] = []

    def _fake(ctx: CliContext) -> CloudAzClient:
        captured.append(ctx)
        return _mock_cloudaz_client()

    monkeypatch.setattr(_client_factory, "make_cloudaz_client", _fake)
    return captured


@pytest.fixture
def login_ctx(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> list[CliContext]:
    _isolate_cache(tmp_path, monkeypatch)
    return _capture_factory(monkeypatch)


def _seed_cache(tmp_path: object, *keys: str):
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


_ALPHA_KEY = (
    "https://alpha.example.com/cas/oidc/accessToken|alice|ControlCenterOIDCClient"
)
_BETA_KEY = "https://beta.example.com/cas/oidc/accessToken|bob|ControlCenterOIDCClient"


def test_login_prompts_for_password_when_missing(login_ctx):
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
    assert "s3cret" not in result.output
    assert login_ctx and login_ctx[0].password == "s3cret"
    assert login_ctx[0].base_url == "https://example.com"
    assert login_ctx[0].username == "admin"


def test_login_prompts_for_everything_when_no_cache_and_no_flags(login_ctx):
    result = runner.invoke(
        app,
        ["auth", "login"],
        input="https://example.com\nadmin\ns3cret\n",
    )

    assert result.exit_code == 0, result.output
    assert login_ctx[0].base_url == "https://example.com"
    assert login_ctx[0].username == "admin"
    assert login_ctx[0].password == "s3cret"


def test_login_shows_menu_when_cache_has_entries_and_flags_missing(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
):
    _isolate_cache(tmp_path, monkeypatch)
    _seed_cache(tmp_path, _ALPHA_KEY, _BETA_KEY)
    captured = _capture_factory(monkeypatch)

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
):
    _isolate_cache(tmp_path, monkeypatch)
    _seed_cache(tmp_path, _ALPHA_KEY)
    captured = _capture_factory(monkeypatch)

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
):
    _isolate_cache(tmp_path, monkeypatch)
    _seed_cache(tmp_path, _ALPHA_KEY)
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
    assert "alice" not in result.output
    assert captured[0].base_url == "https://beta.example.com"
    assert captured[0].username == "bob"


def test_login_menu_selection_does_not_override_explicit_username(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
):
    _isolate_cache(tmp_path, monkeypatch)
    _seed_cache(tmp_path, _ALPHA_KEY)
    captured = _capture_factory(monkeypatch)

    result = runner.invoke(
        app,
        ["--username", "carol", "auth", "login"],
        input="1\ns3cret\n",
    )

    assert result.exit_code == 0, result.output
    assert captured[0].base_url == "https://alpha.example.com"
    assert captured[0].username == "carol"


def test_login_persists_verify_preference_default_true(login_ctx):
    import os

    cache_dir = os.environ["NEXTLABS_CACHE_DIR"]

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
    from nextlabs_sdk._cli._account_preferences_store import AccountPreferencesStore

    store = AccountPreferencesStore(path=f"{cache_dir}/account_prefs.json")
    entry = store.load("https://example.com|admin|ControlCenterOIDCClient")
    assert entry is not None
    assert entry.verify_ssl is True


def test_login_persists_verify_false_when_no_verify_passed(login_ctx):
    import os

    cache_dir = os.environ["NEXTLABS_CACHE_DIR"]

    result = runner.invoke(
        app,
        [
            "--no-verify",
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
    from nextlabs_sdk._cli._account_preferences_store import AccountPreferencesStore

    store = AccountPreferencesStore(path=f"{cache_dir}/account_prefs.json")
    entry = store.load("https://example.com|admin|ControlCenterOIDCClient")
    assert entry is not None
    assert entry.verify_ssl is False


def test_logout_deletes_persisted_preference(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
):
    from nextlabs_sdk._auth._active_account._active_account import ActiveAccount
    from nextlabs_sdk._auth._active_account._active_account_store import (
        ActiveAccountStore,
    )
    from nextlabs_sdk._cli._account_preferences import AccountPreferences
    from nextlabs_sdk._cli._account_preferences_store import AccountPreferencesStore

    _isolate_cache(tmp_path, monkeypatch)
    _seed_cache(tmp_path, _ALPHA_KEY)
    ActiveAccountStore(path=f"{tmp_path}/active_account.json").save(
        ActiveAccount(
            base_url="https://alpha.example.com",
            username="alice",
            client_id="ControlCenterOIDCClient",
        ),
    )
    prefs_path = f"{tmp_path}/account_prefs.json"
    prefs_store = AccountPreferencesStore(path=prefs_path)
    prefs_key = "https://alpha.example.com|alice|ControlCenterOIDCClient"
    prefs_store.save(prefs_key, AccountPreferences(verify_ssl=False))

    result = runner.invoke(app, ["auth", "logout"])

    assert result.exit_code == 0, result.output
    assert prefs_store.load(prefs_key) is None


def _seed_status_cache(tmp_path: object, *, refresh_expires_at: float | None):
    from nextlabs_sdk._auth._active_account._active_account import ActiveAccount
    from nextlabs_sdk._auth._active_account._active_account_store import (
        ActiveAccountStore,
    )
    from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
    from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache

    cache = FileTokenCache(path=f"{tmp_path}/tokens.json")
    cache.save(
        "https://example.com/cas/oidc/accessToken|admin|ControlCenterOIDCClient",
        CachedToken(
            access_token="t",
            refresh_token="rt",
            expires_at=9_999_999_999.0,
            token_type="bearer",
            scope=None,
            refresh_expires_at=refresh_expires_at,
        ),
    )
    ActiveAccountStore(path=f"{tmp_path}/active_account.json").save(
        ActiveAccount(
            base_url="https://example.com",
            username="admin",
            client_id="ControlCenterOIDCClient",
        ),
    )


def test_status_shows_refresh_expires_when_known(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
):
    _isolate_cache(tmp_path, monkeypatch)
    _seed_status_cache(tmp_path, refresh_expires_at=8_888_888_888.0)

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0, result.output
    # Refresh expires epoch 8_888_888_888 -> 2251-09-05 UTC
    assert "2251-09-05" in result.output


def test_status_omits_refresh_expires_when_unknown(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
):
    _isolate_cache(tmp_path, monkeypatch)
    _seed_status_cache(tmp_path, refresh_expires_at=None)

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0, result.output
    assert "2251-09-05" not in result.output
    # Expires epoch 9_999_999_999 -> 2286-11-20 UTC
    assert "2286-11-20" in result.output
    assert "Refresh expires" in result.output
    assert "\u2014" in result.output  # em-dash placeholder


def test_status_shows_account_details(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
):
    _isolate_cache(tmp_path, monkeypatch)
    _seed_status_cache(tmp_path, refresh_expires_at=None)

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0, result.output
    assert "admin" in result.output
    assert "https://example.com" in result.output
    assert "ControlCenterOIDCClient" in result.output
    assert "valid" in result.output


def test_status_expired_exits_with_details(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
):
    from nextlabs_sdk._auth._active_account._active_account import ActiveAccount
    from nextlabs_sdk._auth._active_account._active_account_store import (
        ActiveAccountStore,
    )
    from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
    from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache

    _isolate_cache(tmp_path, monkeypatch)
    FileTokenCache(path=f"{tmp_path}/tokens.json").save(
        "https://example.com/cas/oidc/accessToken|admin|ControlCenterOIDCClient",
        CachedToken(
            access_token="t",
            refresh_token="rt",
            expires_at=1_000.0,
            token_type="bearer",
            scope=None,
            refresh_expires_at=None,
        ),
    )
    ActiveAccountStore(path=f"{tmp_path}/active_account.json").save(
        ActiveAccount(
            base_url="https://example.com",
            username="admin",
            client_id="ControlCenterOIDCClient",
        ),
    )

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 1
    assert "expired" in result.output
    assert "admin" in result.output


def test_status_all_humanizes_expiry(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
):
    _isolate_cache(tmp_path, monkeypatch)
    _seed_status_cache(tmp_path, refresh_expires_at=None)

    result = runner.invoke(app, ["auth", "status", "--all"])

    assert result.exit_code == 0, result.output
    assert "expires_at=" not in result.output
    # Accept wrapping within the Rich table column
    assert "2286" in result.output


def test_status_shows_refreshable_row(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
):
    _isolate_cache(tmp_path, monkeypatch)
    _seed_status_cache(tmp_path, refresh_expires_at=8_888_888_888.0)

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0, result.output
    assert "Refreshable" in result.output


def test_status_refreshable_is_no_when_refresh_known_expired(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
):
    from nextlabs_sdk._auth._active_account._active_account import ActiveAccount
    from nextlabs_sdk._auth._active_account._active_account_store import (
        ActiveAccountStore,
    )
    from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
    from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache

    _isolate_cache(tmp_path, monkeypatch)
    FileTokenCache(path=f"{tmp_path}/tokens.json").save(
        "https://example.com/cas/oidc/accessToken|admin|ControlCenterOIDCClient",
        CachedToken(
            access_token="t",
            refresh_token="rt",
            expires_at=9_999_999_999.0,
            token_type="bearer",
            scope=None,
            refresh_expires_at=1_000.0,  # known-expired
        ),
    )
    ActiveAccountStore(path=f"{tmp_path}/active_account.json").save(
        ActiveAccount(
            base_url="https://example.com",
            username="admin",
            client_id="ControlCenterOIDCClient",
        ),
    )

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0, result.output
    assert "Refreshable" in result.output
    assert "expired" in result.output


def test_status_all_has_refreshable_column(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
):
    _isolate_cache(tmp_path, monkeypatch)
    _seed_status_cache(tmp_path, refresh_expires_at=8_888_888_888.0)

    result = runner.invoke(app, ["auth", "status", "--all"], env={"COLUMNS": "200"})

    assert result.exit_code == 0, result.output
    assert "Refreshable" in result.output
    assert "yes" in result.output
    assert "; refreshable:" not in result.output
