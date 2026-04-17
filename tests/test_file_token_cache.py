from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache

_NEXTLABS_CACHE_DIR = "NEXTLABS_CACHE_DIR"
_XDG_CACHE_HOME = "XDG_CACHE_HOME"
_HOME = "HOME"


def _tok(access_token: str = "id", expires_at: float = 1000.0) -> CachedToken:
    return CachedToken(
        access_token=access_token,
        refresh_token="rt",
        expires_at=expires_at,
        token_type="bearer",
        scope=None,
    )


def test_load_missing_file_returns_none(tmp_path: Path):
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    assert cache.load("k") is None


def test_save_then_load_roundtrip(tmp_path: Path):
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    cache.save("k", _tok())
    assert cache.load("k") == _tok()


def test_save_creates_file_with_0600_and_dir_with_0700(tmp_path: Path):
    path = tmp_path / "sub" / "tokens.json"
    cache = FileTokenCache(path=path)
    cache.save("k", _tok())

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_multiple_keys_isolated_in_same_file(tmp_path: Path):
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    cache.save("a", _tok(access_token="A"))
    cache.save("b", _tok(access_token="B"))

    loaded_a = cache.load("a")
    loaded_b = cache.load("b")
    assert loaded_a is not None and loaded_a.access_token == "A"
    assert loaded_b is not None and loaded_b.access_token == "B"


def test_delete_removes_only_matching_entry(tmp_path: Path):
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    cache.save("a", _tok(access_token="A"))
    cache.save("b", _tok(access_token="B"))

    cache.delete("a")

    assert cache.load("a") is None
    assert cache.load("b") is not None


def test_corrupt_file_returns_none(tmp_path: Path):
    path = tmp_path / "tokens.json"
    path.write_text("{ this is not valid JSON")
    cache = FileTokenCache(path=path)

    assert cache.load("k") is None


def test_save_is_atomic_no_stale_tmp_files(tmp_path: Path):
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    cache.save("k", _tok())

    assert [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_keys_returns_empty_when_file_missing(tmp_path: Path):
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    assert cache.keys() == []


def test_keys_returns_inserted_keys_in_order(tmp_path: Path):
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    cache.save("first", _tok(access_token="1"))
    cache.save("second", _tok(access_token="2"))
    cache.save("third", _tok(access_token="3"))

    assert cache.keys() == ["first", "second", "third"]


def test_keys_reflects_deletions(tmp_path: Path):
    cache = FileTokenCache(path=tmp_path / "tokens.json")
    cache.save("a", _tok())
    cache.save("b", _tok())
    cache.delete("a")

    assert cache.keys() == ["b"]


@pytest.mark.parametrize(
    "set_env,unset_env,suffix",
    [
        pytest.param(
            _NEXTLABS_CACHE_DIR,
            (_XDG_CACHE_HOME,),
            ("tokens.json",),
            id="nextlabs-cache-dir",
        ),
        pytest.param(
            _XDG_CACHE_HOME,
            (_NEXTLABS_CACHE_DIR,),
            ("nextlabs-sdk", "tokens.json"),
            id="xdg-cache-home",
        ),
        pytest.param(
            _HOME,
            (_NEXTLABS_CACHE_DIR, _XDG_CACHE_HOME),
            (".cache", "nextlabs-sdk", "tokens.json"),
            id="home-fallback",
        ),
    ],
)
def test_default_path_env_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    set_env: str,
    unset_env: tuple[str, ...],
    suffix: tuple[str, ...],
):
    for name in unset_env:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(set_env, str(tmp_path))

    cache = FileTokenCache()

    expected = tmp_path
    for part in suffix:
        expected /= part
    assert cache.path == expected


def test_save_recovers_from_corrupt_file_on_disk(tmp_path: Path):
    path = tmp_path / "tokens.json"
    path.write_text("not JSON")
    cache = FileTokenCache(path=path)

    cache.save("k", _tok())

    with path.open() as fh:
        loaded = json.load(fh)
    assert "k" in loaded
