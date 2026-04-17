from __future__ import annotations

import contextlib
import time

import httpx
import pytest
from mockito import when

from nextlabs_sdk._auth._cloudaz_auth import CloudAzAuth
from nextlabs_sdk import exceptions

TOKEN_URL = "https://cloudaz.example.com/cas/oidc/accessToken"


def _make_auth() -> CloudAzAuth:
    return CloudAzAuth(
        token_url=TOKEN_URL,
        username="admin",
        password="secret",
        client_id="ControlCenterOIDCClient",
    )


def _make_token_response(
    id_token: str = "test-id-token",
    expires_in: int = 1200,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id_token": id_token,
            "access_token": "AT-unused",
            "refresh_token": "RT-unused",
            "expires_in": expires_in,
            "token_type": "bearer",
        },
        request=httpx.Request("POST", TOKEN_URL),
    )


def test_first_request_acquires_token() -> None:
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    request = httpx.Request(
        "GET",
        "https://cloudaz.example.com/console/api/v1/tags",
    )

    flow = auth.auth_flow(request)
    token_request = next(flow)

    assert str(token_request.url) == TOKEN_URL
    assert token_request.method == "POST"

    api_request = flow.send(_make_token_response())

    assert "Authorization" in api_request.headers
    assert api_request.headers["Authorization"] == "Bearer test-id-token"


def test_cached_token_skips_token_request() -> None:
    when(time).time().thenReturn(float(0)).thenReturn(100.0)
    auth = _make_auth()
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow1 = auth.auth_flow(request)
    next(flow1)
    flow1.send(_make_token_response(expires_in=1200))
    with contextlib.suppress(StopIteration):
        flow1.send(httpx.Response(200, request=request))

    flow2 = auth.auth_flow(request)
    api_req2 = next(flow2)

    assert api_req2.headers["Authorization"] == "Bearer test-id-token"
    assert str(api_req2.url) != TOKEN_URL


def test_expired_token_triggers_reauth() -> None:
    when(time).time().thenReturn(float(0)).thenReturn(1200.0)
    auth = _make_auth()
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow1 = auth.auth_flow(request)
    next(flow1)
    flow1.send(_make_token_response(expires_in=1200))
    with contextlib.suppress(StopIteration):
        flow1.send(httpx.Response(200, request=request))

    flow2 = auth.auth_flow(request)
    token_req2 = next(flow2)

    assert str(token_req2.url) == TOKEN_URL


def test_401_triggers_reauth() -> None:
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    next(flow)
    flow.send(_make_token_response(id_token="token-v1"))
    reauth_token_request = flow.send(
        httpx.Response(401, request=request),
    )

    assert str(reauth_token_request.url) == TOKEN_URL

    retry_request = flow.send(
        _make_token_response(id_token="token-v2"),
    )

    assert retry_request.headers["Authorization"] == "Bearer token-v2"


def test_token_acquisition_failure_raises() -> None:
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    next(flow)

    with pytest.raises(exceptions.AuthenticationError) as exc_info:
        flow.send(
            httpx.Response(
                401,
                text="Invalid credentials",
                request=httpx.Request("POST", TOKEN_URL),
            ),
        )

    assert exc_info.value.status_code == 401


def test_non_json_200_token_response_raises_authentication_error() -> None:
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    next(flow)

    with pytest.raises(exceptions.AuthenticationError) as exc_info:
        flow.send(
            httpx.Response(
                200,
                content=b"<html>service unavailable</html>",
                request=httpx.Request("POST", TOKEN_URL),
            ),
        )

    assert "Invalid JSON response" in exc_info.value.message


def test_token_response_missing_id_token_raises_authentication_error() -> None:
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    next(flow)

    with pytest.raises(exceptions.AuthenticationError) as exc_info:
        flow.send(
            httpx.Response(
                200,
                json={"expires_in": 1200, "token_type": "bearer"},
                request=httpx.Request("POST", TOKEN_URL),
            ),
        )

    assert "missing 'id_token'" in exc_info.value.message


from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._token_cache import TokenCache


class _InMemoryTokenCache(TokenCache):
    def __init__(self) -> None:
        self.entries: dict[str, CachedToken] = {}

    def load(self, key: str) -> CachedToken | None:
        return self.entries.get(key)

    def save(self, key: str, token: CachedToken) -> None:
        self.entries[key] = token

    def delete(self, key: str) -> None:
        self.entries.pop(key, None)

    def keys(self) -> list[str]:
        return list(self.entries.keys())


_DERIVED_KEY = f"{TOKEN_URL}|admin|ControlCenterOIDCClient"


def _auth_with_cache(
    cache: TokenCache,
    *,
    password: str | None = "secret",
) -> CloudAzAuth:
    return CloudAzAuth(
        token_url=TOKEN_URL,
        username="admin",
        password=password,
        client_id="ControlCenterOIDCClient",
        token_cache=cache,
    )


def test_restores_valid_token_from_cache_without_network() -> None:
    when(time).time().thenReturn(100.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = CachedToken(
        id_token="cached",
        refresh_token=None,
        expires_at=10_000.0,
        token_type="bearer",
        scope=None,
    )

    auth = _auth_with_cache(cache)
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    api_request = next(flow)

    assert api_request.headers["Authorization"] == "Bearer cached"


def test_saves_token_to_cache_after_fresh_acquire() -> None:
    when(time).time().thenReturn(100.0)
    cache = _InMemoryTokenCache()
    auth = _auth_with_cache(cache)
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    next(flow)
    flow.send(_make_token_response(id_token="fresh", expires_in=1200))

    saved = cache.entries[_DERIVED_KEY]
    assert saved.id_token == "fresh"
    assert saved.expires_at == pytest.approx(100.0 + 1200 - 60)


def test_expired_cached_token_with_refresh_token_uses_refresh_grant() -> None:
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = CachedToken(
        id_token="stale",
        refresh_token="RT-1",
        expires_at=float(0),
        token_type="bearer",
        scope=None,
    )

    auth = _auth_with_cache(cache, password=None)
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    token_req = next(flow)

    assert token_req.method == "POST"
    body = bytes(token_req.content).decode()
    assert "grant_type=refresh_token" in body
    assert "refresh_token=RT-1" in body

    api_req = flow.send(_make_token_response(id_token="refreshed"))
    assert api_req.headers["Authorization"] == "Bearer refreshed"


def test_refresh_failure_falls_back_to_password_grant() -> None:
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = CachedToken(
        id_token="stale",
        refresh_token="RT-bad",
        expires_at=float(0),
        token_type="bearer",
        scope=None,
    )

    auth = _auth_with_cache(cache)
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    next(flow)
    pw_req = flow.send(
        httpx.Response(
            401,
            text="bad refresh",
            request=httpx.Request("POST", TOKEN_URL),
        ),
    )

    body = bytes(pw_req.content).decode()
    assert "grant_type=password" in body

    api_req = flow.send(_make_token_response(id_token="pw-token"))
    assert api_req.headers["Authorization"] == "Bearer pw-token"


def test_refresh_failure_without_password_raises() -> None:
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = CachedToken(
        id_token="stale",
        refresh_token="RT-bad",
        expires_at=float(0),
        token_type="bearer",
        scope=None,
    )

    auth = _auth_with_cache(cache, password=None)
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    next(flow)

    with pytest.raises(exceptions.AuthenticationError) as exc_info:
        flow.send(
            httpx.Response(
                401,
                text="bad refresh",
                request=httpx.Request("POST", TOKEN_URL),
            ),
        )

    assert "auth login" in exc_info.value.message.lower()


def test_no_cache_behaves_like_null_cache() -> None:
    when(time).time().thenReturn(100.0)
    auth = CloudAzAuth(
        token_url=TOKEN_URL,
        username="admin",
        password="secret",
        client_id="ControlCenterOIDCClient",
    )
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    token_req = next(flow)
    assert str(token_req.url) == TOKEN_URL
