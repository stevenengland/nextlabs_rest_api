from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache


def _tok(access_token: str = "id", expires_at: float = 1000.0) -> CachedToken:
    return CachedToken(
        access_token=access_token,
        refresh_token="rt",
        expires_at=expires_at,
        token_type="bearer",
        scope=None,
    )


def test_load_missing_file_returns_none(tmp_path: Path) -> None:
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    assert cache.load("k") is None


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    cache.save("k", _tok())
    assert cache.load("k") == _tok()


def test_save_creates_file_with_0600_and_dir_with_0700(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "tokens.json"
    cache = FileTokenCache(path=path)
    cache.save("k", _tok())

    file_mode = stat.S_IMODE(path.stat().st_mode)
    dir_mode = stat.S_IMODE(path.parent.stat().st_mode)
    assert file_mode == 0o600
    assert dir_mode == 0o700


def test_multiple_keys_isolated_in_same_file(tmp_path: Path) -> None:
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    cache.save("a", _tok(access_token="A"))
    cache.save("b", _tok(access_token="B"))

    loaded_a = cache.load("a")
    loaded_b = cache.load("b")
    assert loaded_a is not None and loaded_a.access_token == "A"
    assert loaded_b is not None and loaded_b.access_token == "B"


def test_delete_removes_only_matching_entry(tmp_path: Path) -> None:
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    cache.save("a", _tok(access_token="A"))
    cache.save("b", _tok(access_token="B"))

    cache.delete("a")

    assert cache.load("a") is None
    assert cache.load("b") is not None


def test_corrupt_file_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "tokens.json"
    path.write_text("{ this is not valid JSON")
    cache = FileTokenCache(path=path)

    assert cache.load("k") is None


def test_save_is_atomic_no_stale_tmp_files(tmp_path: Path) -> None:
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    cache.save("k", _tok())

    leftovers = [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


def test_keys_returns_empty_when_file_missing(tmp_path: Path) -> None:
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    assert cache.keys() == []


def test_keys_returns_inserted_keys_in_order(tmp_path: Path) -> None:
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    cache.save("first", _tok(access_token="1"))
    cache.save("second", _tok(access_token="2"))
    cache.save("third", _tok(access_token="3"))

    assert cache.keys() == ["first", "second", "third"]


def test_keys_reflects_deletions(tmp_path: Path) -> None:
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    cache.save("a", _tok())
    cache.save("b", _tok())
    cache.delete("a")

    assert cache.keys() == ["b"]


def test_default_path_respects_nextlabs_cache_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEXTLABS_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)

    cache = FileTokenCache()

    assert cache.path == tmp_path / "tokens.json"


def test_default_path_respects_xdg_cache_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NEXTLABS_CACHE_DIR", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    cache = FileTokenCache()

    assert cache.path == tmp_path / "nextlabs-sdk" / "tokens.json"


def test_default_path_falls_back_to_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NEXTLABS_CACHE_DIR", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    cache = FileTokenCache()

    assert cache.path == tmp_path / ".cache" / "nextlabs-sdk" / "tokens.json"


def test_save_recovers_from_corrupt_file_on_disk(tmp_path: Path) -> None:
    path = tmp_path / "tokens.json"
    path.write_text("not JSON")
    cache = FileTokenCache(path=path)

    cache.save("k", _tok())

    with path.open() as fh:
        data = json.load(fh)
    assert "k" in data
