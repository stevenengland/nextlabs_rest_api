from __future__ import annotations

from nextlabs_sdk._auth._token_cache._cached_token import CachedToken


def test_roundtrip_to_dict_and_back() -> None:
    original = CachedToken(
        access_token="id",
        refresh_token="rt",
        expires_at=1_700_000_000.0,
        token_type="bearer",
        scope="openid",
    )

    restored = CachedToken.from_dict(original.to_dict())

    assert restored == original


def test_from_dict_tolerates_missing_optional_fields() -> None:
    restored = CachedToken.from_dict(
        {
            "access_token": "id",
            "expires_at": 1_700_000_000.0,
            "token_type": "bearer",
        },
    )

    assert restored.refresh_token is None
    assert restored.scope is None


def test_is_expired_uses_absolute_utc_with_safety_margin() -> None:
    token = CachedToken(
        access_token="id",
        refresh_token=None,
        expires_at=1_000.0,
        token_type="bearer",
        scope=None,
    )

    assert token.is_expired(now=1_000.0) is True
    assert token.is_expired(now=900.0, safety_margin=60) is False
    assert token.is_expired(now=950.0, safety_margin=60) is True
