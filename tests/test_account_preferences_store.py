from __future__ import annotations

import stat
from pathlib import Path

import pytest

from nextlabs_sdk._cli._account_preferences import AccountPreferences
from nextlabs_sdk._cli._account_preferences_store import AccountPreferencesStore


def _prefs(verify_ssl: bool = False) -> AccountPreferences:
    return AccountPreferences(verify_ssl=verify_ssl)


def test_load_missing_file_returns_none(tmp_path: Path) -> None:
    store = AccountPreferencesStore(path=tmp_path / "account_prefs.json")
    assert store.load("k") is None


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    store = AccountPreferencesStore(path=tmp_path / "account_prefs.json")
    store.save("k", _prefs(verify_ssl=False))
    assert store.load("k") == _prefs(verify_ssl=False)


def test_multiple_keys_isolated_in_same_file(tmp_path: Path) -> None:
    store = AccountPreferencesStore(path=tmp_path / "account_prefs.json")
    store.save("a", _prefs(verify_ssl=False))
    store.save("b", _prefs(verify_ssl=True))

    assert store.load("a") == _prefs(verify_ssl=False)
    assert store.load("b") == _prefs(verify_ssl=True)


def test_save_overwrites_previous(tmp_path: Path) -> None:
    store = AccountPreferencesStore(path=tmp_path / "account_prefs.json")
    store.save("k", _prefs(verify_ssl=False))
    store.save("k", _prefs(verify_ssl=True))
    assert store.load("k") == _prefs(verify_ssl=True)


def test_delete_removes_only_matching_entry(tmp_path: Path) -> None:
    store = AccountPreferencesStore(path=tmp_path / "account_prefs.json")
    store.save("a", _prefs(verify_ssl=False))
    store.save("b", _prefs(verify_ssl=True))

    store.delete("a")

    assert store.load("a") is None
    assert store.load("b") == _prefs(verify_ssl=True)


def test_delete_missing_key_is_noop(tmp_path: Path) -> None:
    store = AccountPreferencesStore(path=tmp_path / "account_prefs.json")
    store.delete("nope")
    assert store.keys() == []


def test_keys_reports_all_entries(tmp_path: Path) -> None:
    store = AccountPreferencesStore(path=tmp_path / "account_prefs.json")
    store.save("a", _prefs())
    store.save("b", _prefs())
    assert sorted(store.keys()) == ["a", "b"]


def test_save_creates_file_with_0600_and_dir_with_0700(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "account_prefs.json"
    store = AccountPreferencesStore(path=path)
    store.save("k", _prefs())

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_save_is_atomic_no_stale_tmp_files(tmp_path: Path) -> None:
    store = AccountPreferencesStore(path=tmp_path / "account_prefs.json")
    store.save("k", _prefs())

    leftovers = [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


@pytest.mark.parametrize(
    "contents",
    [
        pytest.param("{ not JSON", id="corrupt-json"),
        pytest.param("[1, 2, 3]", id="non-dict-payload"),
    ],
)
def test_load_returns_none_for_malformed_file(
    tmp_path: Path,
    contents: str,
) -> None:
    path = tmp_path / "account_prefs.json"
    path.write_text(contents)
    store = AccountPreferencesStore(path=path)

    assert store.load("k") is None


def test_load_returns_none_for_entry_missing_schema(tmp_path: Path) -> None:
    path = tmp_path / "account_prefs.json"
    path.write_text('{"k": {"verify_ssl": false}}')
    store = AccountPreferencesStore(path=path)

    assert store.load("k") is None


def test_load_returns_none_for_entry_with_bad_type(tmp_path: Path) -> None:
    path = tmp_path / "account_prefs.json"
    path.write_text('{"k": {"schema_version": 1, "verify_ssl": "yes"}}')
    store = AccountPreferencesStore(path=path)

    assert store.load("k") is None


@pytest.mark.parametrize(
    "set_env,unset_env,expected_suffix",
    [
        pytest.param(
            ("NEXTLABS_CACHE_DIR", "{tmp}"),
            ("XDG_CACHE_HOME",),
            "account_prefs.json",
            id="nextlabs-cache-dir",
        ),
        pytest.param(
            ("XDG_CACHE_HOME", "{tmp}"),
            ("NEXTLABS_CACHE_DIR",),
            "nextlabs-sdk/account_prefs.json",
            id="xdg-cache-home",
        ),
        pytest.param(
            ("HOME", "{tmp}"),
            ("NEXTLABS_CACHE_DIR", "XDG_CACHE_HOME"),
            ".cache/nextlabs-sdk/account_prefs.json",
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

    store = AccountPreferencesStore()

    assert store.path == tmp_path / expected_suffix
