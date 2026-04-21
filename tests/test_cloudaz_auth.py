from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import Any

import httpx
import pytest
from mockito import when

from nextlabs_sdk import exceptions
from nextlabs_sdk._auth._cloudaz_auth import CloudAzAuth
from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache
from nextlabs_sdk._auth._token_cache._token_cache import TokenCache

TOKEN_URL = "https://cloudaz.example.com/cas/oidc/accessToken"
API_URL = "https://cloudaz.example.com/api"
_DERIVED_KEY = f"{TOKEN_URL}|admin|ControlCenterOIDCClient|cloudaz"


def _make_auth(
    *,
    password: str | None = "secret",
    token_cache: TokenCache | None = None,
    lifetime: int | None = None,
) -> CloudAzAuth:
    kwargs: dict[str, Any] = dict(
        token_url=TOKEN_URL,
        username="admin",
        password=password,
        client_id="ControlCenterOIDCClient",
    )
    if token_cache is not None:
        kwargs["token_cache"] = token_cache
    auth = CloudAzAuth(**kwargs)
    if lifetime is not None:
        auth.refresh_token_lifetime = lifetime
    return auth


_UNSET: Any = object()


def _make_token_response(
    access_token: str = "test-access-token",
    expires_in: int = 1200,
    id_token: Any = _UNSET,
    refresh_token: str = "RT-unused",
    include_id_token: bool = True,
) -> httpx.Response:
    body: dict[str, Any] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
        "token_type": "bearer",
    }
    if include_id_token:
        body["id_token"] = access_token if id_token is _UNSET else id_token
    return httpx.Response(
        200,
        json=body,
        request=httpx.Request("POST", TOKEN_URL),
    )


def _api_request(url: str = API_URL) -> httpx.Request:
    return httpx.Request("GET", url)


def _token_error_response(
    status: int = 401, text: str = "Invalid credentials"
) -> httpx.Response:
    return httpx.Response(status, text=text, request=httpx.Request("POST", TOKEN_URL))


# ────────────────────────────── basic flow ──────────────────────────────


def test_first_request_acquires_token():
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    flow = auth.auth_flow(
        httpx.Request("GET", "https://cloudaz.example.com/console/api/v1/tags"),
    )
    token_request = next(flow)

    assert str(token_request.url) == TOKEN_URL
    assert token_request.method == "POST"

    api_request = flow.send(_make_token_response())
    assert api_request.headers["Authorization"] == "Bearer test-access-token"


def test_cached_token_skips_token_request():
    when(time).time().thenReturn(float(0)).thenReturn(100.0)
    auth = _make_auth()
    request = _api_request()

    flow1 = auth.auth_flow(request)
    next(flow1)
    flow1.send(_make_token_response(expires_in=1200))
    with contextlib.suppress(StopIteration):
        flow1.send(httpx.Response(200, request=request))

    flow2 = auth.auth_flow(request)
    api_req2 = next(flow2)

    assert api_req2.headers["Authorization"] == "Bearer test-access-token"
    assert str(api_req2.url) != TOKEN_URL


def test_expired_token_triggers_reauth():
    when(time).time().thenReturn(float(0)).thenReturn(1200.0)
    auth = _make_auth()
    request = _api_request()

    flow1 = auth.auth_flow(request)
    next(flow1)
    flow1.send(_make_token_response(expires_in=1200))
    with contextlib.suppress(StopIteration):
        flow1.send(httpx.Response(200, request=request))

    flow2 = auth.auth_flow(request)
    assert str(next(flow2).url) == TOKEN_URL


def test_401_triggers_reauth():
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    request = _api_request()

    flow = auth.auth_flow(request)
    next(flow)
    flow.send(_make_token_response(access_token="token-v1"))
    reauth_token_request = flow.send(httpx.Response(401, request=request))

    assert str(reauth_token_request.url) == TOKEN_URL

    retry_request = flow.send(_make_token_response(access_token="token-v2"))
    assert retry_request.headers["Authorization"] == "Bearer token-v2"


@pytest.mark.parametrize(
    "response,match",
    [
        pytest.param(
            httpx.Response(
                401,
                text="Invalid credentials",
                request=httpx.Request("POST", TOKEN_URL),
            ),
            None,
            id="http-401",
        ),
        pytest.param(
            httpx.Response(
                200,
                content=b"<html>service unavailable</html>",
                request=httpx.Request("POST", TOKEN_URL),
            ),
            "Invalid JSON response",
            id="non-json-200",
        ),
        pytest.param(
            httpx.Response(
                200,
                json={"expires_in": 1200, "token_type": "bearer"},
                request=httpx.Request("POST", TOKEN_URL),
            ),
            "missing 'access_token'",
            id="missing-access-token",
        ),
    ],
)
def test_token_acquisition_failure_raises(response: httpx.Response, match: str | None):
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    flow = auth.auth_flow(_api_request())
    next(flow)

    with pytest.raises(exceptions.AuthenticationError) as exc_info:
        flow.send(response)

    if match is None:
        assert exc_info.value.status_code == 401
    else:
        assert match in exc_info.value.message


# ────────────────────────────── token cache ──────────────────────────────


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


def _cached(
    *,
    access_token: str = "stale",
    refresh_token: str | None = "RT-1",
    expires_at: float | None = None,
    refresh_expires_at: float | None = None,
    id_token: Any = _UNSET,
) -> CachedToken:
    return CachedToken(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=float(0) if expires_at is None else expires_at,
        token_type="bearer",
        scope=None,
        id_token=access_token if id_token is _UNSET else id_token,
        refresh_expires_at=refresh_expires_at,
    )


def test_restores_valid_token_from_cache_without_network():
    when(time).time().thenReturn(100.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = _cached(
        access_token="cached",
        refresh_token=None,
        expires_at=10_000.0,
    )
    auth = _make_auth(token_cache=cache)

    flow = auth.auth_flow(_api_request())
    api_request = next(flow)
    assert api_request.headers["Authorization"] == "Bearer cached"


def test_saves_token_to_cache_after_fresh_acquire():
    when(time).time().thenReturn(100.0)
    cache = _InMemoryTokenCache()
    auth = _make_auth(token_cache=cache)

    flow = auth.auth_flow(_api_request())
    next(flow)
    flow.send(_make_token_response(access_token="fresh", expires_in=1200))

    saved = cache.entries[_DERIVED_KEY]
    assert saved.access_token == "fresh"
    assert saved.expires_at == pytest.approx(100.0 + 1200 - 60)


def test_expired_cached_token_with_refresh_token_uses_refresh_grant():
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = _cached(refresh_token="RT-1")
    auth = _make_auth(password=None, token_cache=cache)

    flow = auth.auth_flow(_api_request())
    token_req = next(flow)

    assert token_req.method == "POST"
    body = bytes(token_req.content).decode()
    assert "grant_type=refresh_token" in body
    assert "refresh_token=RT-1" in body

    api_req = flow.send(_make_token_response(access_token="refreshed"))
    assert api_req.headers["Authorization"] == "Bearer refreshed"


def test_refresh_failure_falls_back_to_password_grant():
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = _cached(refresh_token="RT-bad")
    auth = _make_auth(token_cache=cache)

    flow = auth.auth_flow(_api_request())
    next(flow)
    pw_req = flow.send(_token_error_response(text="bad refresh"))

    assert "grant_type=password" in bytes(pw_req.content).decode()

    api_req = flow.send(_make_token_response(access_token="pw-token"))
    assert api_req.headers["Authorization"] == "Bearer pw-token"


def test_refresh_failure_without_password_raises():
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = _cached(refresh_token="RT-bad")
    auth = _make_auth(password=None, token_cache=cache)

    flow = auth.auth_flow(_api_request())
    next(flow)

    with pytest.raises(exceptions.AuthenticationError) as exc_info:
        flow.send(_token_error_response(text="bad refresh"))

    assert "auth login" in exc_info.value.message.lower()


@pytest.mark.parametrize(
    "status,body",
    [
        pytest.param(400, "invalid_grant", id="status-400"),
        pytest.param(401, "token rejected", id="status-401"),
        pytest.param(403, "forbidden", id="status-403"),
    ],
)
def test_refresh_rejection_populates_error_with_status_and_body(status: int, body: str):
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = _cached(refresh_token="RT-bad")
    auth = _make_auth(password=None, token_cache=cache)

    flow = auth.auth_flow(_api_request())
    next(flow)

    with pytest.raises(exceptions.RefreshTokenExpiredError) as exc_info:
        flow.send(_token_error_response(status=status, text=body))

    exc = exc_info.value
    assert exc.status_code == status
    assert exc.response_body == body
    assert exc.request_url == TOKEN_URL


def test_refresh_spa_redirect_raises_refresh_token_expired():
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = _cached(refresh_token="RT-bad")
    auth = _make_auth(password=None, token_cache=cache)

    spa_redirect = httpx.Response(
        302,
        headers={"location": "https://cloudaz.example.com/#/login"},
        request=httpx.Request("POST", TOKEN_URL),
    )

    flow = auth.auth_flow(_api_request())
    next(flow)

    with pytest.raises(exceptions.RefreshTokenExpiredError) as exc_info:
        flow.send(spa_redirect)

    assert exc_info.value.status_code == 302


def test_refresh_body_preview_stays_within_limit_and_reports_byte_length():
    from nextlabs_sdk._auth import _cloudaz_auth as mod

    body_chars = "€" * (mod._RESPONSE_BODY_PREVIEW_LIMIT + 100)
    assert len(body_chars.encode("utf-8")) > len(body_chars)

    preview = mod._truncate_body(body_chars, len(body_chars.encode("utf-8")))

    assert len(preview) <= mod._RESPONSE_BODY_PREVIEW_LIMIT
    assert preview.endswith(
        f"truncated, {len(body_chars.encode('utf-8'))} bytes total)",
    )
    assert "truncated" in preview


def test_refresh_body_short_bodies_returned_verbatim():
    from nextlabs_sdk._auth import _cloudaz_auth as mod

    short = "hello"

    assert mod._truncate_body(short, len(short.encode("utf-8"))) == short


def test_refresh_rejection_populates_byte_length_from_response_content():
    from nextlabs_sdk._auth import _cloudaz_auth as mod

    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = _cached(refresh_token="RT-bad")
    auth = _make_auth(password=None, token_cache=cache)

    flow = auth.auth_flow(_api_request())
    next(flow)
    body_chars = "€" * (mod._RESPONSE_BODY_PREVIEW_LIMIT + 100)
    with pytest.raises(exceptions.RefreshTokenExpiredError) as exc_info:
        flow.send(_token_error_response(status=400, text=body_chars))

    preview = exc_info.value.response_body or ""
    assert len(preview) <= mod._RESPONSE_BODY_PREVIEW_LIMIT
    assert f"{len(body_chars.encode('utf-8'))} bytes total" in preview


def test_no_cache_behaves_like_null_cache():
    when(time).time().thenReturn(100.0)
    auth = _make_auth()
    flow = auth.auth_flow(_api_request())
    assert str(next(flow).url) == TOKEN_URL


# ─────────────────────────── SPA-hash redirect ───────────────────────────


def _make_spa_redirect_response(
    request: httpx.Request,
    location: str = "https://cloudaz.example.com/#/policy-studio/analytics/dashboard",
) -> httpx.Response:
    redirect = httpx.Response(302, headers={"location": location}, request=request)
    final = httpx.Response(
        200,
        content=b"<!doctype html><html></html>",
        headers={"content-type": "text/html"},
        request=httpx.Request("GET", location),
    )
    final.history = [redirect]
    return final


def test_spa_hash_redirect_triggers_reauth():
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    request = _api_request()

    flow = auth.auth_flow(request)
    next(flow)
    flow.send(_make_token_response(access_token="v1"))
    reauth_token_req = flow.send(_make_spa_redirect_response(request))

    assert str(reauth_token_req.url) == TOKEN_URL

    retry_req = flow.send(_make_token_response(access_token="v2"))
    assert retry_req.headers["Authorization"] == "Bearer v2"


def test_persistent_spa_hash_redirect_raises_authentication_error():
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    request = _api_request()

    flow = auth.auth_flow(request)
    next(flow)
    flow.send(_make_token_response(access_token="v1"))
    flow.send(_make_spa_redirect_response(request))
    flow.send(_make_token_response(access_token="v2"))

    with pytest.raises(exceptions.AuthenticationError) as exc_info:
        flow.send(_make_spa_redirect_response(request))

    assert "SPA login page" in exc_info.value.message
    assert "auth login" in exc_info.value.message.lower()


def test_non_hash_redirect_does_not_trigger_reauth():
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    request = _api_request("https://cloudaz.example.com/api/v1/foo")

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


# ─────────────────────────── ensure_token ──────────────────


def _run_ensure_token(
    auth: CloudAzAuth,
    responses: list[httpx.Response],
) -> list[httpx.Request]:
    sent: list[httpx.Request] = []

    def send(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return responses.pop(0)

    auth.ensure_token(send)
    return sent


def test_ensure_token_noop_when_valid_token_cached():
    when(time).time().thenReturn(float(0))
    auth = _make_auth()

    request = _api_request()
    flow = auth.auth_flow(request)
    next(flow)
    flow.send(_make_token_response(access_token="already", expires_in=1200))
    with contextlib.suppress(StopIteration):
        flow.send(httpx.Response(200, request=request))

    assert _run_ensure_token(auth, []) == []


def test_ensure_token_uses_password_grant_when_no_refresh():
    when(time).time().thenReturn(float(0))
    auth = _make_auth()

    sent = _run_ensure_token(auth, [_make_token_response(access_token="fresh")])

    assert len(sent) == 1
    assert str(sent[0].url) == TOKEN_URL
    assert "grant_type=password" in sent[0].content.decode()
    assert auth._id_token == "fresh"


def test_ensure_token_prefers_refresh_token_when_available():
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    auth._refresh_token = "RT-cached"

    sent = _run_ensure_token(auth, [_make_token_response(access_token="refreshed")])

    assert len(sent) == 1
    body = sent[0].content.decode()
    assert "grant_type=refresh_token" in body
    assert "refresh_token=RT-cached" in body
    assert auth._id_token == "refreshed"


def test_ensure_token_falls_back_to_password_when_refresh_fails():
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    auth._refresh_token = "RT-stale"

    sent = _run_ensure_token(
        auth,
        [
            _token_error_response(text="invalid_grant"),
            _make_token_response(access_token="pwd-grant"),
        ],
    )

    assert len(sent) == 2
    assert "grant_type=refresh_token" in sent[0].content.decode()
    assert "grant_type=password" in sent[1].content.decode()
    assert auth._id_token == "pwd-grant"


def test_ensure_token_raises_when_no_password_and_refresh_fails():
    when(time).time().thenReturn(float(0))
    auth = _make_auth(password=None)
    auth._refresh_token = "RT-stale"

    with pytest.raises(exceptions.AuthenticationError) as exc_info:
        _run_ensure_token(auth, [_token_error_response(text="invalid_grant")])

    assert "auth login" in exc_info.value.message.lower()


def test_ensure_token_caches_access_token(tmp_path: object):
    when(time).time().thenReturn(float(0))
    cache = FileTokenCache(path=f"{tmp_path}/tokens.json")
    auth = _make_auth(token_cache=cache)

    _run_ensure_token(auth, [_make_token_response(access_token="persisted")])

    loaded = cache.load(auth._cache_key)
    assert loaded is not None
    assert loaded.access_token == "persisted"


def test_ensure_token_async_fetches_and_caches():
    when(time).time().thenReturn(float(0))
    auth = _make_auth()

    sent: list[httpx.Request] = []

    async def send(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return _make_token_response(access_token="async-fresh")

    asyncio.run(auth.ensure_token_async(send))

    assert len(sent) == 1
    assert auth._id_token == "async-fresh"


# ─────────────── Proactive refresh-token-lifetime tracking ───────────────


def test_refresh_token_lifetime_populates_refresh_expires_at():
    when(time).time().thenReturn(1000.0)
    cache = _InMemoryTokenCache()
    auth = _make_auth(token_cache=cache, lifetime=86_400)

    flow = auth.auth_flow(_api_request())
    next(flow)
    flow.send(_make_token_response(access_token="fresh", expires_in=1200))

    saved = cache.entries[_DERIVED_KEY]
    assert saved.refresh_expires_at == pytest.approx(1000.0 + 86_400)


def test_no_lifetime_leaves_refresh_expires_at_none():
    when(time).time().thenReturn(1000.0)
    cache = _InMemoryTokenCache()
    auth = _make_auth(token_cache=cache)  # no lifetime → reactive mode

    flow = auth.auth_flow(_api_request())
    next(flow)
    flow.send(_make_token_response(access_token="fresh"))

    assert cache.entries[_DERIVED_KEY].refresh_expires_at is None


def test_known_expired_refresh_skips_http_call_and_uses_password():
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = _cached(
        refresh_token="RT-stale",
        refresh_expires_at=9_000.0,
    )
    auth = _make_auth(token_cache=cache, lifetime=86_400)

    flow = auth.auth_flow(_api_request())
    body = bytes(next(flow).content).decode()

    assert "grant_type=password" in body
    assert "grant_type=refresh_token" not in body


def test_known_expired_refresh_without_password_raises_refresh_token_expired():
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = _cached(
        refresh_token="RT-stale",
        refresh_expires_at=9_000.0,
    )
    auth = _make_auth(password=None, token_cache=cache, lifetime=86_400)

    flow = auth.auth_flow(_api_request())

    with pytest.raises(exceptions.RefreshTokenExpiredError) as exc_info:
        next(flow)

    assert "lifetime exceeded" in exc_info.value.message.lower()
    assert "auth login" in exc_info.value.message.lower()


def test_reactive_rejection_without_password_raises_refresh_token_expired():
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = _cached(refresh_token="RT-dead")
    auth = _make_auth(password=None, token_cache=cache)

    flow = auth.auth_flow(_api_request())
    next(flow)

    with pytest.raises(exceptions.RefreshTokenExpiredError) as exc_info:
        flow.send(_token_error_response(text="invalid_grant"))

    assert "rejected by server" in exc_info.value.message.lower()
    assert "auth login" in exc_info.value.message.lower()


def test_refresh_token_expired_is_authentication_error_subclass():
    assert issubclass(
        exceptions.RefreshTokenExpiredError,
        exceptions.AuthenticationError,
    )


def test_ensure_token_async_known_expired_skips_refresh_http_call():
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = _cached(
        refresh_token="RT-stale",
        refresh_expires_at=9_000.0,
    )
    auth = _make_auth(token_cache=cache, lifetime=86_400)
    sent: list[httpx.Request] = []

    async def send(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return _make_token_response(access_token="async-pw")

    asyncio.run(auth.ensure_token_async(send))

    assert len(sent) == 1
    assert "grant_type=password" in sent[0].content.decode()


def test_logs_refresh_attempt_and_success(caplog: pytest.LogCaptureFixture):
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = _cached(refresh_token="RT-good")
    auth = _make_auth(token_cache=cache)

    caplog.set_level(logging.DEBUG, logger="nextlabs_sdk")
    flow = auth.auth_flow(_api_request())
    next(flow)
    flow.send(_make_token_response(access_token="refreshed"))

    messages = [r.getMessage() for r in caplog.records]
    assert any("refresh attempt starting" in m for m in messages)
    assert any("refresh succeeded" in m for m in messages)


def test_logs_warning_on_terminal_refresh_failure(caplog: pytest.LogCaptureFixture):
    when(time).time().thenReturn(10_000.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = _cached(refresh_token="RT-dead")
    auth = _make_auth(password=None, token_cache=cache)

    caplog.set_level(logging.WARNING, logger="nextlabs_sdk")
    flow = auth.auth_flow(_api_request())
    next(flow)

    with pytest.raises(exceptions.RefreshTokenExpiredError):
        flow.send(_token_error_response(text="invalid_grant"))

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings
    assert any("refresh token rejected" in r.getMessage().lower() for r in warnings)
    for record in caplog.records:
        assert "RT-dead" not in record.getMessage()


# ────────────────────────── id_token bearer (OIDC) ──────────────────────────


def test_authorization_header_uses_id_token_not_access_token():
    when(time).time().thenReturn(float(0))
    auth = _make_auth()

    flow = auth.auth_flow(_api_request())
    next(flow)
    api_request = flow.send(
        _make_token_response(access_token="AT-value", id_token="IDT-value"),
    )

    assert api_request.headers["Authorization"] == "Bearer IDT-value"
    assert "AT-value" not in api_request.headers["Authorization"]


def test_cache_persists_both_access_and_id_token():
    when(time).time().thenReturn(100.0)
    cache = _InMemoryTokenCache()
    auth = _make_auth(token_cache=cache)

    flow = auth.auth_flow(_api_request())
    next(flow)
    flow.send(_make_token_response(access_token="AT-1", id_token="IDT-1"))

    saved = cache.entries[_DERIVED_KEY]
    assert saved.access_token == "AT-1"
    assert saved.id_token == "IDT-1"


def test_response_missing_id_token_falls_back_to_access_token_with_warning(
    caplog: pytest.LogCaptureFixture,
):
    when(time).time().thenReturn(float(0))
    auth = _make_auth()
    caplog.set_level(logging.WARNING, logger="nextlabs_sdk")

    flow = auth.auth_flow(_api_request())
    next(flow)
    api_request = flow.send(
        _make_token_response(access_token="AT-only", include_id_token=False),
    )

    assert api_request.headers["Authorization"] == "Bearer AT-only"
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("missing id_token" in r.getMessage().lower() for r in warnings)


def test_legacy_cache_without_id_token_triggers_silent_refresh_not_relogin():
    when(time).time().thenReturn(100.0)
    cache = _InMemoryTokenCache()
    cache.entries[_DERIVED_KEY] = _cached(
        access_token="legacy-at",
        refresh_token="RT-legacy",
        expires_at=10_000.0,
        id_token=None,
    )
    auth = _make_auth(password=None, token_cache=cache)

    flow = auth.auth_flow(_api_request())
    token_req = next(flow)

    body = bytes(token_req.content).decode()
    assert "grant_type=refresh_token" in body
    assert "refresh_token=RT-legacy" in body

    api_request = flow.send(
        _make_token_response(access_token="AT-new", id_token="IDT-new"),
    )
    assert api_request.headers["Authorization"] == "Bearer IDT-new"
    assert cache.entries[_DERIVED_KEY].id_token == "IDT-new"
