from __future__ import annotations

import json
import stat
from pathlib import Path

from mockito import spy2, verify

from nextlabs_sdk._auth._token_cache import _secret_box as sb
from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._encrypted_file_token_cache import (
    EncryptedFileTokenCache,
)
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
