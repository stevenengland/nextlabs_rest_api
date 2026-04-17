from __future__ import annotations

import stat
from pathlib import Path

import pytest

from nextlabs_sdk._auth._active_account._active_account import ActiveAccount
from nextlabs_sdk._auth._active_account._active_account_store import (
    ActiveAccountStore,
)


def _account(
    base_url: str = "https://example.com",
    username: str = "alice",
    client_id: str = "ControlCenterOIDCClient",
) -> ActiveAccount:
    return ActiveAccount(base_url=base_url, username=username, client_id=client_id)


def test_load_missing_file_returns_none(tmp_path: Path) -> None:
    store = ActiveAccountStore(path=tmp_path / "active_account.json")
    assert store.load() is None


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    store = ActiveAccountStore(path=tmp_path / "active_account.json")
    store.save(_account())
    assert store.load() == _account()


def test_save_creates_file_with_0600_and_dir_with_0700(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "active_account.json"
    store = ActiveAccountStore(path=path)
    store.save(_account())

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_clear_removes_file(tmp_path: Path) -> None:
    path = tmp_path / "active_account.json"
    store = ActiveAccountStore(path=path)
    store.save(_account())

    store.clear()

    assert not path.exists()
    assert store.load() is None


def test_clear_is_noop_when_missing(tmp_path: Path) -> None:
    store = ActiveAccountStore(path=tmp_path / "active_account.json")
    store.clear()
    assert store.load() is None


@pytest.mark.parametrize(
    "contents",
    [
        pytest.param("{ not JSON", id="corrupt-json"),
        pytest.param("[1, 2, 3]", id="non-dict-payload"),
        pytest.param('{"base_url": "https://x", "username": "u"}', id="missing-fields"),
    ],
)
def test_load_rejects_invalid_file(tmp_path: Path, contents: str) -> None:
    path = tmp_path / "active_account.json"
    path.write_text(contents)
    store = ActiveAccountStore(path=path)

    assert store.load() is None


def test_save_overwrites_previous(tmp_path: Path) -> None:
    store = ActiveAccountStore(path=tmp_path / "active_account.json")
    store.save(_account(username="alice"))
    store.save(_account(username="bob"))

    loaded = store.load()
    assert loaded is not None
    assert loaded.username == "bob"


def test_save_is_atomic_no_stale_tmp_files(tmp_path: Path) -> None:
    store = ActiveAccountStore(path=tmp_path / "active_account.json")
    store.save(_account())

    leftovers = [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


@pytest.mark.parametrize(
    "set_env,unset_env,expected_suffix",
    [
        pytest.param(
            ("NEXTLABS_CACHE_DIR", "{tmp}"),
            ("XDG_CACHE_HOME",),
            "active_account.json",
            id="nextlabs-cache-dir",
        ),
        pytest.param(
            ("XDG_CACHE_HOME", "{tmp}"),
            ("NEXTLABS_CACHE_DIR",),
            "nextlabs-sdk/active_account.json",
            id="xdg-cache-home",
        ),
        pytest.param(
            ("HOME", "{tmp}"),
            ("NEXTLABS_CACHE_DIR", "XDG_CACHE_HOME"),
            ".cache/nextlabs-sdk/active_account.json",
            id="home-fallback",
        ),
    ],
)
def test_default_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    set_env: tuple[str, str],
    unset_env: tuple[str, ...],
    expected_suffix: str,
) -> None:
    for name in unset_env:
        monkeypatch.delenv(name, raising=False)
    env_name, env_value = set_env
    monkeypatch.setenv(env_name, env_value.format(tmp=str(tmp_path)))

    store = ActiveAccountStore()

    assert store.path == tmp_path / expected_suffix
