from __future__ import annotations

from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._null_token_cache import NullTokenCache


def _sample() -> CachedToken:
    return CachedToken(
        access_token="id",
        refresh_token=None,
        expires_at=1.0,
        token_type="bearer",
        scope=None,
    )


def test_load_returns_none_before_and_after_save():
    cache = NullTokenCache()
    assert cache.load("any-key") is None
    cache.save("k", _sample())
    assert cache.load("k") is None


def test_delete_is_noop():
    NullTokenCache().delete("k")


def test_keys_returns_empty_list():
    assert NullTokenCache().keys() == []
