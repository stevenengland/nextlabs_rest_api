from __future__ import annotations

from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._null_token_cache import NullTokenCache


def _sample() -> CachedToken:
    return CachedToken(
        id_token="id",
        refresh_token=None,
        expires_at=1.0,
        token_type="bearer",
        scope=None,
    )


def test_load_returns_none() -> None:
    cache = NullTokenCache()
    assert cache.load("any-key") is None


def test_save_is_noop_and_load_still_returns_none() -> None:
    cache = NullTokenCache()
    cache.save("k", _sample())
    assert cache.load("k") is None


def test_delete_is_noop() -> None:
    NullTokenCache().delete("k")
