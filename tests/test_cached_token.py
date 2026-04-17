from __future__ import annotations

from typing import Any

import pytest

from nextlabs_sdk._auth._token_cache._cached_token import CachedToken


def _base_dict() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "access_token": "id",
        "expires_at": 1_700_000_000.0,
        "token_type": "bearer",
    }


def _make_token(**overrides: Any) -> CachedToken:
    defaults: dict[str, Any] = {
        "access_token": "id",
        "refresh_token": "rt",
        "expires_at": 1_700_000_000.0,
        "token_type": "bearer",
        "scope": "openid",
    }
    defaults.update(overrides)
    return CachedToken(**defaults)


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({}, id="basic"),
        pytest.param(
            {"refresh_expires_at": 1_700_003_600.0}, id="with-refresh-expires"
        ),
    ],
)
def test_roundtrip_to_dict_and_back(overrides):
    original = _make_token(**overrides)

    restored = CachedToken.from_dict(original.to_dict())

    assert restored == original
    expected_refresh = overrides.get("refresh_expires_at")
    if expected_refresh is not None:
        assert restored.refresh_expires_at == pytest.approx(expected_refresh)


def test_from_dict_tolerates_missing_optional_fields():
    restored = CachedToken.from_dict(_base_dict())

    assert restored.refresh_token is None
    assert restored.scope is None
    assert restored.refresh_expires_at is None


@pytest.mark.parametrize(
    "schema_version_patch",
    [
        pytest.param({}, id="missing"),
        pytest.param({"schema_version": 1}, id="older"),
    ],
)
def test_from_dict_rejects_invalid_schema_version(schema_version_patch):
    payload = {
        "access_token": "id",
        "expires_at": 1_700_000_000.0,
        "token_type": "bearer",
        **schema_version_patch,
    }
    with pytest.raises(TypeError):
        CachedToken.from_dict(payload)


def test_is_expired_uses_absolute_utc_with_safety_margin():
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
