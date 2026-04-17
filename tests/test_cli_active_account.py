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

ALPHA = "https://alpha.example.com"
BETA = "https://beta.example.com"
CLIENT = "ControlCenterOIDCClient"
ACC_ALICE = (ALPHA, "alice", CLIENT)
ACC_BOB = (BETA, "bob", CLIENT)


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
            {"base_url": base_url, "username": username, "client_id": client_id}
        ),
    )


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _isolate(tmp_path, monkeypatch)
    return tmp_path


# ─────────────────────────── login → active ───────────────────────────────


@pytest.mark.parametrize(
    "pre_active,base_url,username,expected",
    [
        pytest.param(
            None,
            ALPHA,
            "alice",
            {"base_url": ALPHA, "username": "alice", "client_id": CLIENT},
            id="promote-new",
        ),
        pytest.param(
            ("https://old.example.com", "old", CLIENT),
            "https://new.example.com",
            "newbie",
            {
                "base_url": "https://new.example.com",
                "username": "newbie",
                "client_id": CLIENT,
            },
            id="overwrite-existing",
        ),
    ],
)
def test_login_sets_active(
    env: Path,
    monkeypatch: pytest.MonkeyPatch,
    pre_active: tuple[str, str, str] | None,
    base_url: str,
    username: str,
    expected: dict[str, str],
):
    if pre_active is not None:
        _write_active(env, *pre_active)
    _capture_factory(monkeypatch)

    result = runner.invoke(
        app,
        ["--base-url", base_url, "--username", username, "auth", "login"],
        input="s3cret\n",
    )

    assert result.exit_code == 0, result.output
    assert _read_active(env) == expected


# ─────────────────────────── status ──────────────────────────────────────


def test_status_uses_active_when_no_flags(env: Path):
    _seed_cache(env, ACC_ALICE)
    _write_active(env, *ACC_ALICE)

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0, result.output
    assert "valid" in result.output.lower()


def test_status_without_active_prints_remediation(env: Path):
    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 1
    assert "auth login" in result.output
    assert "auth use" in result.output


def test_status_all_lists_every_account(env: Path):
    _seed_cache(env, ACC_ALICE, ACC_BOB)
    _write_active(env, *ACC_BOB)

    result = runner.invoke(app, ["auth", "status", "--all"])

    assert result.exit_code == 0, result.output
    assert "alice" in result.output
    assert "bob" in result.output
    assert "*" in result.output  # active marker


def test_status_all_empty_exits_nonzero(env: Path):
    result = runner.invoke(app, ["auth", "status", "--all"])
    assert result.exit_code == 1
    assert "auth login" in result.output


# ─────────────────────────── accounts subcommand ──────────────────────────


def test_accounts_lists_with_active_marker(env: Path):
    _seed_cache(env, ACC_ALICE, ACC_BOB)
    _write_active(env, *ACC_BOB)

    result = runner.invoke(app, ["auth", "accounts"])

    assert result.exit_code == 0, result.output
    assert "alice" in result.output
    assert "bob" in result.output


def test_accounts_empty_exits_nonzero(env: Path):
    result = runner.invoke(app, ["auth", "accounts"])
    assert result.exit_code == 1
    assert "auth login" in result.output


# ─────────────────────────── use subcommand ───────────────────────────────


@pytest.mark.parametrize(
    "accounts,args,stdin,expected_username",
    [
        pytest.param(
            [ACC_ALICE, ACC_BOB],
            ["auth", "use", "2"],
            None,
            "bob",
            id="by-index",
        ),
        pytest.param(
            [ACC_ALICE, ACC_BOB],
            ["auth", "use", f"alice@{ALPHA}"],
            None,
            "alice",
            id="by-user-at-base-url",
        ),
        pytest.param(
            [ACC_ALICE, ACC_BOB],
            ["auth", "use"],
            "2\n",
            "bob",
            id="interactive",
        ),
    ],
)
def test_use_selects_active_account(
    env: Path,
    accounts: list[tuple[str, str, str]],
    args: list[str],
    stdin: str | None,
    expected_username: str,
):
    _seed_cache(env, *accounts)

    result = (
        runner.invoke(app, args, input=stdin) if stdin else runner.invoke(app, args)
    )

    assert result.exit_code == 0, result.output
    active = _read_active(env)
    assert active is not None
    assert active["username"] == expected_username


@pytest.mark.parametrize(
    "accounts,args,expected_in_output",
    [
        pytest.param([ACC_ALICE], ["auth", "use", "9"], "9", id="unknown-index"),
        pytest.param(
            [ACC_ALICE],
            ["auth", "use", "ghost@https://nope.example.com"],
            "ghost",
            id="unknown-selector",
        ),
        pytest.param([], ["auth", "use"], "auth login", id="empty-cache"),
    ],
)
def test_use_failure_modes(
    env: Path,
    accounts: list[tuple[str, str, str]],
    args: list[str],
    expected_in_output: str,
):
    if accounts:
        _seed_cache(env, *accounts)

    result = runner.invoke(app, args)

    assert result.exit_code == 1
    assert expected_in_output in result.output


# ─────────────────────────── logout ───────────────────────────────────────


def test_logout_uses_active_when_no_flags(env: Path):
    _seed_cache(env, ACC_ALICE)
    _write_active(env, *ACC_ALICE)

    result = runner.invoke(app, ["auth", "logout"])

    assert result.exit_code == 0, result.output
    cache = FileTokenCache(path=env / "tokens.json")
    assert cache.keys() == []
    assert _read_active(env) is None


def test_logout_without_active_prints_remediation(env: Path):
    result = runner.invoke(app, ["auth", "logout"])

    assert result.exit_code == 1
    assert "auth login" in result.output


def test_logout_explicit_flags_does_not_clear_unrelated_active(env: Path):
    _seed_cache(env, ACC_ALICE, ACC_BOB)
    _write_active(env, *ACC_BOB)

    result = runner.invoke(
        app,
        ["--base-url", ALPHA, "--username", "alice", "auth", "logout"],
    )

    assert result.exit_code == 0, result.output
    active = _read_active(env)
    assert active is not None
    assert active["username"] == "bob"


# ─────────────────────────── factory fallback ─────────────────────────────


def test_factory_uses_active_when_no_flags(env: Path):
    _seed_cache(env, ACC_ALICE)
    _write_active(env, *ACC_ALICE)
    when(_client_factory).make_cloudaz_client(...).thenReturn(_mock_cloudaz_client())

    result = runner.invoke(app, ["auth", "test"])

    assert result.exit_code == 0, result.output


def test_factory_error_mentions_login_and_use(env: Path):
    result = runner.invoke(app, ["auth", "test"])

    assert result.exit_code == 1
    assert "auth login" in result.output
    assert "auth use" in result.output
