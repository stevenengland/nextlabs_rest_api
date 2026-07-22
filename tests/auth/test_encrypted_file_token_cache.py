from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest
from mockito import spy2, verify, when

from nextlabs_sdk._auth._token_cache import _secret_box as sb
from nextlabs_sdk import CachedToken
from nextlabs_sdk import EncryptedFileTokenCache
from nextlabs_sdk._auth._token_cache._secret_box import PassphraseKek


def _kek() -> PassphraseKek:
    return PassphraseKek(passphrase=b"hunter2")


def _tok(access_token: str = "id", expires_at: float = 1000.0) -> CachedToken:
    return CachedToken(
        access_token=access_token,
        refresh_token="rt",
        expires_at=expires_at,
        token_type="bearer",
        scope=None,
    )


def test_encrypted_round_trip_and_magic(tmp_path: Path):
    path = tmp_path / "tokens.json"
    cache = EncryptedFileTokenCache(path=path, kek_source=_kek())
    tok = _tok()
    cache.save("acct", tok)

    assert path.read_bytes().startswith(b"NLBX")
    fresh = EncryptedFileTokenCache(path=path, kek_source=_kek())
    assert fresh.load("acct") == tok
    # POSIX-mode bits are not enforceable on Windows; chmod is a no-op there.
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_legacy_plaintext_loads_then_save_encrypts(tmp_path: Path):
    path = tmp_path / "tokens.json"
    tok = _tok()
    path.write_text(json.dumps({"acct": tok.to_dict()}), encoding="utf-8")
    cache = EncryptedFileTokenCache(path=path, kek_source=_kek())

    assert cache.load("acct") == tok
    assert not path.read_bytes().startswith(b"NLBX")

    cache.save("acct2", _tok())
    assert path.read_bytes().startswith(b"NLBX")


def test_argon2_runs_once_per_process(tmp_path: Path):
    spy2(sb._derive_kek)
    path = tmp_path / "tokens.json"
    cache = EncryptedFileTokenCache(path=path, kek_source=_kek())

    cache.save("a", _tok())
    cache.save("b", _tok())
    cache.load("a")

    verify(sb, times=1)._derive_kek(...)


def test_loading_legacy_file_does_not_rewrite_it(tmp_path: Path):
    # Given a legacy plaintext cache file
    path = tmp_path / "tokens.json"
    tok = _tok()
    path.write_text(json.dumps({"acct": tok.to_dict()}), encoding="utf-8")
    original_bytes = path.read_bytes()
    cache = EncryptedFileTokenCache(path=path, kek_source=_kek())

    # When the token is loaded
    loaded = cache.load("acct")

    # Then the same token is returned and the file is left byte-for-byte intact
    assert loaded == tok
    assert path.read_bytes() == original_bytes


def test_first_save_migrates_and_preserves_existing_tokens(tmp_path: Path):
    # Given a legacy plaintext file holding one account
    path = tmp_path / "tokens.json"
    legacy = _tok(access_token="legacy")
    path.write_text(json.dumps({"acct": legacy.to_dict()}), encoding="utf-8")
    cache = EncryptedFileTokenCache(path=path, kek_source=_kek())

    # When a second account is saved
    added = _tok(access_token="added")
    cache.save("acct2", added)

    # Then the file is encrypted and decrypts to both the old and new tokens
    assert path.read_bytes().startswith(b"NLBX")
    fresh = EncryptedFileTokenCache(path=path, kek_source=_kek())
    assert fresh.load("acct") == legacy
    assert fresh.load("acct2") == added


def test_failed_write_leaves_plaintext_intact_and_rerun_completes(tmp_path: Path):
    # Given a legacy plaintext file
    path = tmp_path / "tokens.json"
    legacy = _tok(access_token="legacy")
    path.write_text(json.dumps({"acct": legacy.to_dict()}), encoding="utf-8")
    original_bytes = path.read_bytes()
    cache = EncryptedFileTokenCache(path=path, kek_source=_kek())

    # When the atomic rename fails mid-write
    when(os).replace(...).thenRaise(OSError("disk full"))
    with pytest.raises(OSError):
        cache.save("acct2", _tok(access_token="added"))

    # Then the previous plaintext file is untouched and still readable
    assert path.read_bytes() == original_bytes
    assert EncryptedFileTokenCache(path=path, kek_source=_kek()).load("acct") == legacy

    # And re-running the save after recovery completes the migration,
    # persisting both the existing and the newly-added token
    added = _tok(access_token="added")
    when(os).replace(...).thenCallOriginalImplementation()
    cache.save("acct2", added)
    assert path.read_bytes().startswith(b"NLBX")
    fresh = EncryptedFileTokenCache(path=path, kek_source=_kek())
    assert fresh.load("acct") == legacy
    assert fresh.load("acct2") == added


def test_dir_and_file_modes_preserved_across_migration(tmp_path: Path):
    if os.name != "posix":
        pytest.skip("POSIX-mode bits are not enforceable on Windows")

    # Given a legacy plaintext file inside the cache directory
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    path = cache_dir / "tokens.json"
    path.write_text(json.dumps({"acct": _tok().to_dict()}), encoding="utf-8")
    cache = EncryptedFileTokenCache(path=path, kek_source=_kek())

    # When the first save migrates the file to encrypted form
    cache.save("acct2", _tok())

    # Then the directory is 0700 and the file is 0600
    assert stat.S_IMODE(cache_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
