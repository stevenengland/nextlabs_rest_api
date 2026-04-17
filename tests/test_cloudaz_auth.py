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
    access_token: str = "test-access-token",
    expires_in: int = 1200,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "access_token": access_token,
            "id_token": "ID-unused",
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
    assert api_request.headers["Authorization"] == "Bearer test-access-token"


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

    assert api_req2.headers["Authorization"] == "Bearer test-access-token"
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
    flow.send(_make_token_response(access_token="token-v1"))
    reauth_token_request = flow.send(
        httpx.Response(401, request=request),
    )

    assert str(reauth_token_request.url) == TOKEN_URL

    retry_request = flow.send(
        _make_token_response(access_token="token-v2"),
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


def test_token_response_missing_access_token_raises_authentication_error() -> None:
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

    assert "missing 'access_token'" in exc_info.value.message


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
        access_token="cached",
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
    flow.send(_make_token_response(access_token="fresh", expires_in=1200))

    saved = cache.entries[_DERIVED_KEY]
    assert saved.access_token == "fresh"
    assert saved.expires_at == pytest.approx(100.0 + 1200 - 60)


def test_expired_cached_token_with_refresh_token_uses_refresh_grant() -> None:
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = CachedToken(
        access_token="stale",
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

    api_req = flow.send(_make_token_response(access_token="refreshed"))
    assert api_req.headers["Authorization"] == "Bearer refreshed"


def test_refresh_failure_falls_back_to_password_grant() -> None:
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = CachedToken(
        access_token="stale",
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

    api_req = flow.send(_make_token_response(access_token="pw-token"))
    assert api_req.headers["Authorization"] == "Bearer pw-token"


def test_refresh_failure_without_password_raises() -> None:
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = CachedToken(
        access_token="stale",
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


def _make_spa_redirect_response(
    request: httpx.Request,
    location: str = "https://cloudaz.example.com/#/policy-studio/analytics/dashboard",
) -> httpx.Response:
    redirect = httpx.Response(
        302,
        headers={"location": location},
        request=request,
    )
    final = httpx.Response(
        200,
        content=b"<!doctype html><html></html>",
        headers={"content-type": "text/html"},
        request=httpx.Request("GET", location),
    )
    final.history = [redirect]
    return final


def test_spa_hash_redirect_triggers_reauth() -> None:
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    next(flow)
    flow.send(_make_token_response(access_token="v1"))
    reauth_token_req = flow.send(_make_spa_redirect_response(request))

    assert str(reauth_token_req.url) == TOKEN_URL

    retry_req = flow.send(_make_token_response(access_token="v2"))
    assert retry_req.headers["Authorization"] == "Bearer v2"


def test_persistent_spa_hash_redirect_raises_authentication_error() -> None:
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    next(flow)
    flow.send(_make_token_response(access_token="v1"))
    flow.send(_make_spa_redirect_response(request))
    flow.send(_make_token_response(access_token="v2"))

    with pytest.raises(exceptions.AuthenticationError) as exc_info:
        flow.send(_make_spa_redirect_response(request))

    assert "SPA login page" in exc_info.value.message
    assert "auth login" in exc_info.value.message.lower()


def test_non_hash_redirect_does_not_trigger_reauth() -> None:
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    request = httpx.Request("GET", "https://cloudaz.example.com/api/v1/foo")

    flow = auth.auth_flow(request)
    next(flow)
    flow.send(_make_token_response(access_token="v1"))

    trailing_redirect = httpx.Response(
        302,
        headers={"location": "https://cloudaz.example.com/api/v1/foo/"},
        request=request,
    )
    final_ok = httpx.Response(
        200,
        json={"ok": True},
        request=httpx.Request("GET", "https://cloudaz.example.com/api/v1/foo/"),
    )
    final_ok.history = [trailing_redirect]

    with contextlib.suppress(StopIteration):
        flow.send(final_ok)


# ─────────────────────────── ensure_token (direct fetch) ──────────────────


def _run_ensure_token(
    auth: CloudAzAuth, responses: list[httpx.Response]
) -> list[httpx.Request]:
    """Drive ensure_token with a canned response queue; return sent requests."""
    sent: list[httpx.Request] = []

    def send(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return responses.pop(0)

    auth.ensure_token(send)
    return sent


def test_ensure_token_noop_when_valid_token_cached() -> None:
    when(time).time().thenReturn(float(0))
    auth = _make_auth()

    # Prime an in-memory token via auth_flow.
    request = httpx.Request("GET", "https://cloudaz.example.com/api")
    flow = auth.auth_flow(request)
    next(flow)
    flow.send(_make_token_response(access_token="already", expires_in=1200))
    with contextlib.suppress(StopIteration):
        flow.send(httpx.Response(200, request=request))

    sent = _run_ensure_token(auth, [])
    assert sent == []


def test_ensure_token_uses_password_grant_when_no_refresh() -> None:
    when(time).time().thenReturn(float(0))
    auth = _make_auth()

    sent = _run_ensure_token(auth, [_make_token_response(access_token="fresh")])

    assert len(sent) == 1
    assert str(sent[0].url) == TOKEN_URL
    body = sent[0].content.decode()
    assert "grant_type=password" in body
    assert auth._token == "fresh"


def test_ensure_token_prefers_refresh_token_when_available() -> None:
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    auth._refresh_token = "RT-cached"

    sent = _run_ensure_token(auth, [_make_token_response(access_token="refreshed")])

    assert len(sent) == 1
    body = sent[0].content.decode()
    assert "grant_type=refresh_token" in body
    assert "refresh_token=RT-cached" in body
    assert auth._token == "refreshed"


def test_ensure_token_falls_back_to_password_when_refresh_fails() -> None:
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    auth._refresh_token = "RT-stale"

    refresh_failed = httpx.Response(
        401,
        text="invalid_grant",
        request=httpx.Request("POST", TOKEN_URL),
    )
    sent = _run_ensure_token(
        auth,
        [refresh_failed, _make_token_response(access_token="pwd-grant")],
    )

    assert len(sent) == 2
    assert "grant_type=refresh_token" in sent[0].content.decode()
    assert "grant_type=password" in sent[1].content.decode()
    assert auth._token == "pwd-grant"


def test_ensure_token_raises_when_no_password_and_refresh_fails() -> None:
    when(time).time().thenReturn(float(0))
    auth = CloudAzAuth(
        token_url=TOKEN_URL,
        username="admin",
        password=None,
        client_id="ControlCenterOIDCClient",
    )
    auth._refresh_token = "RT-stale"

    refresh_failed = httpx.Response(
        401,
        text="invalid_grant",
        request=httpx.Request("POST", TOKEN_URL),
    )

    with pytest.raises(exceptions.AuthenticationError) as exc_info:
        _run_ensure_token(auth, [refresh_failed])

    assert "auth login" in exc_info.value.message.lower()


def test_ensure_token_caches_access_token(tmp_path: object) -> None:
    """ensure_token must populate both in-memory state and cache."""
    from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache

    when(time).time().thenReturn(float(0))
    cache = FileTokenCache(path=f"{tmp_path}/tokens.json")
    auth = CloudAzAuth(
        token_url=TOKEN_URL,
        username="admin",
        password="secret",
        client_id="ControlCenterOIDCClient",
        token_cache=cache,
    )

    _run_ensure_token(auth, [_make_token_response(access_token="persisted")])

    loaded = cache.load(auth._cache_key)
    assert loaded is not None
    assert loaded.access_token == "persisted"


def test_ensure_token_async_fetches_and_caches() -> None:
    import asyncio

    when(time).time().thenReturn(float(0))
    auth = _make_auth()

    sent: list[httpx.Request] = []

    async def send(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return _make_token_response(access_token="async-fresh")

    async def run() -> None:
        await auth.ensure_token_async(send)

    asyncio.run(run())

    assert len(sent) == 1
    assert auth._token == "async-fresh"


# ─────────────── Proactive refresh-token-lifetime tracking ───────────────


def _auth_with_lifetime(
    cache: TokenCache,
    *,
    password: str | None = "secret",
    lifetime: int | None = None,
) -> CloudAzAuth:
    auth = CloudAzAuth(
        token_url=TOKEN_URL,
        username="admin",
        password=password,
        client_id="ControlCenterOIDCClient",
        token_cache=cache,
    )
    auth.refresh_token_lifetime = lifetime
    return auth


def test_refresh_token_lifetime_populates_refresh_expires_at() -> None:
    when(time).time().thenReturn(1000.0)
    cache = _InMemoryTokenCache()
    auth = _auth_with_lifetime(cache, lifetime=86_400)
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    next(flow)
    flow.send(_make_token_response(access_token="fresh", expires_in=1200))

    saved = cache.entries[_DERIVED_KEY]
    assert saved.refresh_expires_at == pytest.approx(1000.0 + 86_400)


def test_no_lifetime_leaves_refresh_expires_at_none() -> None:
    when(time).time().thenReturn(1000.0)
    cache = _InMemoryTokenCache()
    auth = _auth_with_lifetime(cache)  # lifetime=None → reactive mode
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    next(flow)
    flow.send(_make_token_response(access_token="fresh"))

    saved = cache.entries[_DERIVED_KEY]
    assert saved.refresh_expires_at is None


def test_known_expired_refresh_skips_http_call_and_uses_password() -> None:
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = CachedToken(
        access_token="stale",
        refresh_token="RT-stale",
        expires_at=float(0),
        token_type="bearer",
        scope=None,
        refresh_expires_at=9_000.0,  # already elapsed
    )

    auth = _auth_with_lifetime(cache, lifetime=86_400)
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    token_req = next(flow)

    # Must go straight to password grant without attempting refresh.
    body = bytes(token_req.content).decode()
    assert "grant_type=password" in body
    assert "grant_type=refresh_token" not in body


def test_known_expired_refresh_without_password_raises_refresh_token_expired() -> None:
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = CachedToken(
        access_token="stale",
        refresh_token="RT-stale",
        expires_at=float(0),
        token_type="bearer",
        scope=None,
        refresh_expires_at=9_000.0,
    )

    auth = _auth_with_lifetime(cache, password=None, lifetime=86_400)
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)

    with pytest.raises(exceptions.RefreshTokenExpiredError) as exc_info:
        next(flow)

    assert "lifetime exceeded" in exc_info.value.message.lower()
    assert "auth login" in exc_info.value.message.lower()


def test_reactive_rejection_without_password_raises_refresh_token_expired() -> None:
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = CachedToken(
        access_token="stale",
        refresh_token="RT-dead",
        expires_at=float(0),
        token_type="bearer",
        scope=None,
        refresh_expires_at=None,  # reactive mode
    )

    auth = _auth_with_lifetime(cache, password=None)
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    flow = auth.auth_flow(request)
    next(flow)  # yields refresh request

    with pytest.raises(exceptions.RefreshTokenExpiredError) as exc_info:
        flow.send(
            httpx.Response(
                401,
                text="invalid_grant",
                request=httpx.Request("POST", TOKEN_URL),
            ),
        )

    assert "rejected by server" in exc_info.value.message.lower()
    assert "auth login" in exc_info.value.message.lower()


def test_refresh_token_expired_is_authentication_error_subclass() -> None:
    assert issubclass(
        exceptions.RefreshTokenExpiredError,
        exceptions.AuthenticationError,
    )


def test_ensure_token_async_known_expired_skips_refresh_http_call() -> None:
    import asyncio

    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = CachedToken(
        access_token="stale",
        refresh_token="RT-stale",
        expires_at=float(0),
        token_type="bearer",
        scope=None,
        refresh_expires_at=9_000.0,
    )

    auth = _auth_with_lifetime(cache, lifetime=86_400)
    sent: list[httpx.Request] = []

    async def send(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return _make_token_response(access_token="async-pw")

    async def run() -> None:
        await auth.ensure_token_async(send)

    asyncio.run(run())

    assert len(sent) == 1
    assert "grant_type=password" in sent[0].content.decode()


def test_logs_refresh_attempt_and_success(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = CachedToken(
        access_token="stale",
        refresh_token="RT-good",
        expires_at=float(0),
        token_type="bearer",
        scope=None,
        refresh_expires_at=None,
    )

    auth = _auth_with_lifetime(cache)
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    caplog.set_level(logging.DEBUG, logger="nextlabs_sdk")
    flow = auth.auth_flow(request)
    next(flow)
    flow.send(_make_token_response(access_token="refreshed"))

    messages = [r.getMessage() for r in caplog.records]
    assert any("refresh attempt starting" in m for m in messages)
    assert any("refresh succeeded" in m for m in messages)


def test_logs_warning_on_terminal_refresh_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = CachedToken(
        access_token="stale",
        refresh_token="RT-dead",
        expires_at=float(0),
        token_type="bearer",
        scope=None,
        refresh_expires_at=None,
    )

    auth = _auth_with_lifetime(cache, password=None)
    request = httpx.Request("GET", "https://cloudaz.example.com/api")

    caplog.set_level(logging.WARNING, logger="nextlabs_sdk")
    flow = auth.auth_flow(request)
    next(flow)

    with pytest.raises(exceptions.RefreshTokenExpiredError):
        flow.send(
            httpx.Response(
                401,
                text="invalid_grant",
                request=httpx.Request("POST", TOKEN_URL),
            ),
        )

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings
    assert any("refresh token rejected" in r.getMessage().lower() for r in warnings)
    # Token values must never appear in log records.
    for record in caplog.records:
        assert "RT-dead" not in record.getMessage()
