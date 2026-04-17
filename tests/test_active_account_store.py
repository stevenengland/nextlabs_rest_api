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
    return ActiveAccount(
        base_url=base_url,
        username=username,
        client_id=client_id,
    )


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

    file_mode = stat.S_IMODE(path.stat().st_mode)
    dir_mode = stat.S_IMODE(path.parent.stat().st_mode)
    assert file_mode == 0o600
    assert dir_mode == 0o700


def test_clear_removes_file(tmp_path: Path) -> None:
    path = tmp_path / "active_account.json"
    store = ActiveAccountStore(path=path)
    store.save(_account())

    store.clear()

    assert not path.exists()
    assert store.load() is None


def test_clear_is_noop_when_missing(tmp_path: Path) -> None:
    store = ActiveAccountStore(path=tmp_path / "active_account.json")
    store.clear()  # should not raise
    assert store.load() is None


def test_corrupt_file_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "active_account.json"
    path.write_text("{ not JSON")
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


def test_load_rejects_non_dict_payload(tmp_path: Path) -> None:
    path = tmp_path / "active_account.json"
    path.write_text("[1, 2, 3]")
    store = ActiveAccountStore(path=path)

    assert store.load() is None


def test_load_rejects_missing_fields(tmp_path: Path) -> None:
    path = tmp_path / "active_account.json"
    path.write_text('{"base_url": "https://x", "username": "u"}')
    store = ActiveAccountStore(path=path)

    assert store.load() is None


def test_default_path_respects_nextlabs_cache_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEXTLABS_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)

    store = ActiveAccountStore()

    assert store.path == tmp_path / "active_account.json"


def test_default_path_respects_xdg_cache_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NEXTLABS_CACHE_DIR", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    store = ActiveAccountStore()

    assert store.path == tmp_path / "nextlabs-sdk" / "active_account.json"


def test_default_path_falls_back_to_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NEXTLABS_CACHE_DIR", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    store = ActiveAccountStore()

    assert store.path == tmp_path / ".cache" / "nextlabs-sdk" / "active_account.json"
