from __future__ import annotations

from pathlib import Path

import pytest
from mockito import when
from typer.testing import CliRunner

from nextlabs_sdk._auth._active_account._active_account import ActiveAccount
from nextlabs_sdk._auth._active_account._active_account_store import (
    ActiveAccountStore,
)
from nextlabs_sdk._auth._token_cache._cache_factory import CacheStatus
from nextlabs_sdk import CachedToken
from nextlabs_sdk import FileTokenCache
from nextlabs_sdk._cli import _auth_cmd
from nextlabs_sdk._cli._account_preferences import GlobalCachePreferences
from nextlabs_sdk._cli._account_preferences_store import AccountPreferencesStore
from nextlabs_sdk._cli._app import app
from nextlabs_sdk.exceptions import TokenCacheError

runner = CliRunner()

_ACTIVE_KEY = (
    "https://example.com/cas/oidc/accessToken" "|admin|ControlCenterOIDCClient|cloudaz"
)


def _isolate_cache(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXTLABS_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("NEXTLABS_DISABLE_TOKEN_ENCRYPTION", "1")
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)


def _set_active_account(tmp_path: object) -> None:
    ActiveAccountStore(path=f"{tmp_path}/active_account.json").save(
        ActiveAccount(
            base_url="https://example.com",
            username="admin",
            client_id="ControlCenterOIDCClient",
        ),
    )


def _seed_plaintext_token(tmp_path: object) -> None:
    FileTokenCache(path=f"{tmp_path}/tokens.json").save(
        _ACTIVE_KEY,
        CachedToken(
            access_token="t",
            refresh_token="rt",
            expires_at=9_999_999_999.0,
            token_type="bearer",
            scope=None,
            refresh_expires_at=None,
        ),
    )
    _set_active_account(tmp_path)


def test_status_prints_cache_line_alongside_validity(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given a valid plaintext token cache on disk
    _isolate_cache(tmp_path, monkeypatch)
    _seed_plaintext_token(tmp_path)

    # When status is rendered
    result = runner.invoke(app, ["auth", "status"])

    # Then both the validity output and a cache line appear
    assert result.exit_code == 0, result.output
    assert "valid" in result.output
    assert "Cache:" in result.output
    assert "tokens.json" in result.output
    assert "plaintext" in result.output
    assert "source:" in result.output
    assert "suite:" in result.output


def test_status_reports_plaintext_for_legacy_file(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given a legacy plaintext token file on disk
    _isolate_cache(tmp_path, monkeypatch)
    _seed_plaintext_token(tmp_path)

    # When status is rendered
    result = runner.invoke(app, ["auth", "status"])

    # Then the encryption state is reported as plaintext
    assert result.exit_code == 0, result.output
    assert "(plaintext)" in result.output


def test_status_prints_cache_line_when_no_token_cached(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given an active account but no cached token file
    _isolate_cache(tmp_path, monkeypatch)
    _set_active_account(tmp_path)

    # When status is rendered
    result = runner.invoke(app, ["auth", "status"])

    # Then the cache line still appears and the exit code is unchanged
    assert result.exit_code == 1, result.output
    assert "Cache:" in result.output
    assert "absent" in result.output
    assert "No cached token." in result.output


@pytest.mark.parametrize("source_label", ["env", "keyring", "tty", "none"])
def test_status_renders_labels_from_read_only_inspector(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
    source_label: str,
) -> None:
    # Given the read-only inspector reports a source label and KDF suite
    _isolate_cache(tmp_path, monkeypatch)
    when(_auth_cmd).inspect_token_cache(...).thenReturn(
        CacheStatus(
            path=Path(f"{tmp_path}/tokens.json"),
            state="encrypted",
            source=source_label,
            suite_id=1,
        )
    )

    # When status is rendered
    result = runner.invoke(app, ["auth", "status"])

    # Then the cache line reflects the inspector's labels without unlocking
    assert "Cache:" in result.output
    assert f"source: {source_label}" in result.output
    assert "suite: argon2id" in result.output


def test_status_labels_raw_wrapped_suite(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given a keyring (raw-key) wrapped cache whose header suite id is 0
    _isolate_cache(tmp_path, monkeypatch)
    when(_auth_cmd).inspect_token_cache(...).thenReturn(
        CacheStatus(
            path=Path(f"{tmp_path}/tokens.json"),
            state="encrypted",
            source="keyring",
            suite_id=0,
        )
    )

    # When status is rendered
    result = runner.invoke(app, ["auth", "status"])

    # Then the raw wrap is labelled rather than shown as a bare integer
    assert "suite: raw" in result.output
    assert "suite: 0" not in result.output


def test_status_survives_unreadable_cache_header(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given a valid token but an inspector that cannot parse the cache header
    _isolate_cache(tmp_path, monkeypatch)
    _seed_plaintext_token(tmp_path)
    when(_auth_cmd).inspect_token_cache(...).thenRaise(TokenCacheError())

    # When status is rendered
    result = runner.invoke(app, ["auth", "status"])

    # Then validity output still appears and the command does not abort
    assert result.exit_code == 0, result.output
    assert "valid" in result.output
    assert "unreadable" in result.output


def test_status_all_prints_cache_line(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given a seeded cache and the --all path
    _isolate_cache(tmp_path, monkeypatch)
    _seed_plaintext_token(tmp_path)

    # When status --all is rendered
    result = runner.invoke(app, ["auth", "status", "--all"])

    # Then the cache line appears on the --all path too
    assert result.exit_code == 0, result.output
    assert "Cache:" in result.output
    assert "plaintext" in result.output


def _remember_plaintext_choice(tmp_path: object) -> None:
    AccountPreferencesStore(path=f"{tmp_path}/account_prefs.json").save_global_cache(
        GlobalCachePreferences(plaintext_acknowledged=True),
    )


def test_status_reports_remembered_plaintext_choice(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given a remembered plaintext-storage choice on disk
    _isolate_cache(tmp_path, monkeypatch)
    _seed_plaintext_token(tmp_path)
    _remember_plaintext_choice(tmp_path)

    # When status is rendered
    result = runner.invoke(app, ["auth", "status"])

    # Then the remembered choice is reported as yes
    assert result.exit_code == 0, result.output
    assert "Remembered plaintext choice: yes" in result.output


def test_status_reports_no_remembered_plaintext_choice(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given no remembered plaintext-storage choice on disk
    _isolate_cache(tmp_path, monkeypatch)
    _seed_plaintext_token(tmp_path)

    # When status is rendered
    result = runner.invoke(app, ["auth", "status"])

    # Then the remembered choice is reported as no
    assert result.exit_code == 0, result.output
    assert "Remembered plaintext choice: no" in result.output
