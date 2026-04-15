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
    when(time).monotonic().thenReturn(float(0))
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
    when(time).monotonic().thenReturn(float(0)).thenReturn(100.0)
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
    when(time).monotonic().thenReturn(float(0)).thenReturn(1200.0)
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
    when(time).monotonic().thenReturn(float(0))
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
    when(time).monotonic().thenReturn(float(0))
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
