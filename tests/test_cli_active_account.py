from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache
from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._operators import OperatorService

runner = CliRunner()


# ─────────────────────────── helpers ──────────────────────────────────────


def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXTLABS_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)


def _mock_cloudaz_client() -> CloudAzClient:
    mock_client = mock(CloudAzClient)
    mock_ops = mock(OperatorService)
    mock_client.operators = mock_ops
    when(mock_ops).list_types().thenReturn(["STRING", "NUMBER"])
    when(mock_client).authenticate().thenReturn(None)
    return cast(CloudAzClient, mock_client)


def _capture_factory(monkeypatch: pytest.MonkeyPatch) -> list[CliContext]:
    captured: list[CliContext] = []

    def _fake(ctx: CliContext) -> CloudAzClient:
        captured.append(ctx)
        return _mock_cloudaz_client()

    monkeypatch.setattr(_client_factory, "make_cloudaz_client", _fake)
    return captured


def _key(base_url: str, username: str, client_id: str) -> str:
    return f"{base_url}/cas/oidc/accessToken|{username}|{client_id}"


def _seed_cache(
    tmp_path: Path,
    *entries: tuple[str, str, str],
    expires_at: float = 1e12,
) -> None:
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    tok = CachedToken(
        access_token="id",
        refresh_token="rt",
        expires_at=expires_at,
        token_type="bearer",
        scope=None,
    )
    for base_url, username, client_id in entries:
        cache.save(_key(base_url, username, client_id), tok)


def _read_active(tmp_path: Path) -> dict[str, str] | None:
    path = tmp_path / "active_account.json"
    if not path.exists():
        return None
    with path.open() as fh:
        return cast(dict[str, str], json.load(fh))


def _write_active(tmp_path: Path, base_url: str, username: str, client_id: str) -> None:
    (tmp_path / "active_account.json").write_text(
        json.dumps(
            {
                "base_url": base_url,
                "username": username,
                "client_id": client_id,
            },
        ),
    )


# ─────────────────────────── login → active ───────────────────────────────


def test_login_promotes_account_to_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    _capture_factory(monkeypatch)

    result = runner.invoke(
        app,
        [
            "--base-url",
            "https://alpha.example.com",
            "--username",
            "alice",
            "auth",
            "login",
        ],
        input="s3cret\n",
    )

    assert result.exit_code == 0, result.output
    assert _read_active(tmp_path) == {
        "base_url": "https://alpha.example.com",
        "username": "alice",
        "client_id": "ControlCenterOIDCClient",
    }


def test_login_overwrites_previous_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    _write_active(tmp_path, "https://old.example.com", "old", "ControlCenterOIDCClient")
    _capture_factory(monkeypatch)

    result = runner.invoke(
        app,
        [
            "--base-url",
            "https://new.example.com",
            "--username",
            "newbie",
            "auth",
            "login",
        ],
        input="s3cret\n",
    )

    assert result.exit_code == 0, result.output
    assert _read_active(tmp_path) == {
        "base_url": "https://new.example.com",
        "username": "newbie",
        "client_id": "ControlCenterOIDCClient",
    }


# ─────────────────────────── status default ───────────────────────────────


def test_status_uses_active_when_no_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    _seed_cache(
        tmp_path,
        ("https://alpha.example.com", "alice", "ControlCenterOIDCClient"),
    )
    _write_active(
        tmp_path,
        "https://alpha.example.com",
        "alice",
        "ControlCenterOIDCClient",
    )

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0, result.output
    assert "valid" in result.output.lower()


def test_status_without_active_prints_remediation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 1
    assert "auth login" in result.output
    assert "auth use" in result.output


def test_status_all_lists_every_account(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    _seed_cache(
        tmp_path,
        ("https://alpha.example.com", "alice", "ControlCenterOIDCClient"),
        ("https://beta.example.com", "bob", "ControlCenterOIDCClient"),
    )
    _write_active(
        tmp_path,
        "https://beta.example.com",
        "bob",
        "ControlCenterOIDCClient",
    )

    result = runner.invoke(app, ["auth", "status", "--all"])

    assert result.exit_code == 0, result.output
    assert "alice" in result.output
    assert "bob" in result.output
    assert "*" in result.output  # active marker


def test_status_all_empty_exits_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    result = runner.invoke(app, ["auth", "status", "--all"])
    assert result.exit_code == 1
    assert "auth login" in result.output


# ─────────────────────────── accounts subcommand ──────────────────────────


def test_accounts_lists_with_active_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    _seed_cache(
        tmp_path,
        ("https://alpha.example.com", "alice", "ControlCenterOIDCClient"),
        ("https://beta.example.com", "bob", "ControlCenterOIDCClient"),
    )
    _write_active(
        tmp_path,
        "https://beta.example.com",
        "bob",
        "ControlCenterOIDCClient",
    )

    result = runner.invoke(app, ["auth", "accounts"])

    assert result.exit_code == 0, result.output
    assert "alice" in result.output
    assert "bob" in result.output


def test_accounts_empty_exits_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    result = runner.invoke(app, ["auth", "accounts"])
    assert result.exit_code == 1
    assert "auth login" in result.output


# ─────────────────────────── use subcommand ───────────────────────────────


def test_use_with_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    _seed_cache(
        tmp_path,
        ("https://alpha.example.com", "alice", "ControlCenterOIDCClient"),
        ("https://beta.example.com", "bob", "ControlCenterOIDCClient"),
    )

    result = runner.invoke(app, ["auth", "use", "2"])

    assert result.exit_code == 0, result.output
    assert _read_active(tmp_path) == {
        "base_url": "https://beta.example.com",
        "username": "bob",
        "client_id": "ControlCenterOIDCClient",
    }


def test_use_with_username_at_base_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    _seed_cache(
        tmp_path,
        ("https://alpha.example.com", "alice", "ControlCenterOIDCClient"),
        ("https://beta.example.com", "bob", "ControlCenterOIDCClient"),
    )

    result = runner.invoke(
        app,
        ["auth", "use", "alice@https://alpha.example.com"],
    )

    assert result.exit_code == 0, result.output
    active = _read_active(tmp_path)
    assert active is not None
    assert active["username"] == "alice"


def test_use_interactive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    _seed_cache(
        tmp_path,
        ("https://alpha.example.com", "alice", "ControlCenterOIDCClient"),
        ("https://beta.example.com", "bob", "ControlCenterOIDCClient"),
    )

    result = runner.invoke(app, ["auth", "use"], input="2\n")

    assert result.exit_code == 0, result.output
    active = _read_active(tmp_path)
    assert active is not None
    assert active["username"] == "bob"


def test_use_unknown_index_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    _seed_cache(
        tmp_path,
        ("https://alpha.example.com", "alice", "ControlCenterOIDCClient"),
    )

    result = runner.invoke(app, ["auth", "use", "9"])

    assert result.exit_code == 1
    assert "9" in result.output


def test_use_unknown_selector_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    _seed_cache(
        tmp_path,
        ("https://alpha.example.com", "alice", "ControlCenterOIDCClient"),
    )

    result = runner.invoke(
        app,
        ["auth", "use", "ghost@https://nope.example.com"],
    )

    assert result.exit_code == 1
    assert "ghost" in result.output


def test_use_empty_cache_exits_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    result = runner.invoke(app, ["auth", "use"])
    assert result.exit_code == 1
    assert "auth login" in result.output


# ─────────────────────────── logout default ───────────────────────────────


def test_logout_uses_active_when_no_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    _seed_cache(
        tmp_path,
        ("https://alpha.example.com", "alice", "ControlCenterOIDCClient"),
    )
    _write_active(
        tmp_path,
        "https://alpha.example.com",
        "alice",
        "ControlCenterOIDCClient",
    )

    result = runner.invoke(app, ["auth", "logout"])

    assert result.exit_code == 0, result.output
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    assert cache.keys() == []
    assert _read_active(tmp_path) is None


def test_logout_without_active_prints_remediation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)

    result = runner.invoke(app, ["auth", "logout"])

    assert result.exit_code == 1
    assert "auth login" in result.output


def test_logout_explicit_flags_does_not_clear_unrelated_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    _seed_cache(
        tmp_path,
        ("https://alpha.example.com", "alice", "ControlCenterOIDCClient"),
        ("https://beta.example.com", "bob", "ControlCenterOIDCClient"),
    )
    _write_active(
        tmp_path,
        "https://beta.example.com",
        "bob",
        "ControlCenterOIDCClient",
    )

    result = runner.invoke(
        app,
        [
            "--base-url",
            "https://alpha.example.com",
            "--username",
            "alice",
            "auth",
            "logout",
        ],
    )

    assert result.exit_code == 0, result.output
    active = _read_active(tmp_path)
    assert active is not None
    assert active["username"] == "bob"


# ─────────────────────────── factory fallback ─────────────────────────────


def test_factory_uses_active_when_no_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    _seed_cache(
        tmp_path,
        ("https://alpha.example.com", "alice", "ControlCenterOIDCClient"),
    )
    _write_active(
        tmp_path,
        "https://alpha.example.com",
        "alice",
        "ControlCenterOIDCClient",
    )
    when(_client_factory).make_cloudaz_client(...).thenReturn(_mock_cloudaz_client())

    # No --base-url / --username on the command line.
    result = runner.invoke(app, ["auth", "test"])

    assert result.exit_code == 0, result.output


def test_factory_error_mentions_login_and_use(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)

    result = runner.invoke(app, ["auth", "test"])

    assert result.exit_code == 1
    assert "auth login" in result.output
    assert "auth use" in result.output
