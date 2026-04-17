from __future__ import annotations

import contextlib
import time

import httpx
import pytest
from mockito import when

from nextlabs_sdk._auth._pdp_auth import PdpAuth
from nextlabs_sdk import exceptions

TOKEN_URL = "https://cloudaz.example.com/cas/token"


def _make_auth() -> PdpAuth:
    return PdpAuth(
        token_url=TOKEN_URL,
        client_id="pdp-client",
        client_secret="pdp-secret",
    )


def _make_token_response(
    access_token: str = "test-access-token",
    expires_in: int = 3600,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in,
        },
        request=httpx.Request("POST", TOKEN_URL),
    )


def test_first_request_acquires_token() -> None:
    when(time).monotonic().thenReturn(float(0))
    auth = _make_auth()
    request = httpx.Request(
        "POST",
        "https://cloudaz.example.com/dpc/authorization/pdp",
    )

    flow = auth.auth_flow(request)
    token_request = next(flow)

    assert str(token_request.url) == TOKEN_URL
    assert token_request.method == "POST"

    api_request = flow.send(_make_token_response())

    assert api_request.headers["Authorization"] == "Bearer test-access-token"


def test_cached_token_skips_token_request() -> None:
    when(time).monotonic().thenReturn(float(0)).thenReturn(100.0)
    auth = _make_auth()
    request = httpx.Request(
        "POST",
        "https://cloudaz.example.com/dpc/authorization/pdp",
    )

    flow1 = auth.auth_flow(request)
    next(flow1)
    flow1.send(_make_token_response(expires_in=3600))
    with contextlib.suppress(StopIteration):
        flow1.send(httpx.Response(200, request=request))

    flow2 = auth.auth_flow(request)
    api_req2 = next(flow2)

    assert api_req2.headers["Authorization"] == "Bearer test-access-token"
    assert str(api_req2.url) != TOKEN_URL


def test_expired_token_triggers_reacquisition() -> None:
    when(time).monotonic().thenReturn(float(0)).thenReturn(4000.0)
    auth = _make_auth()
    request = httpx.Request(
        "POST",
        "https://cloudaz.example.com/dpc/authorization/pdp",
    )

    flow1 = auth.auth_flow(request)
    next(flow1)
    flow1.send(_make_token_response(expires_in=3600))
    with contextlib.suppress(StopIteration):
        flow1.send(httpx.Response(200, request=request))

    flow2 = auth.auth_flow(request)
    token_req2 = next(flow2)

    assert str(token_req2.url) == TOKEN_URL


def test_401_triggers_reacquisition() -> None:
    when(time).monotonic().thenReturn(float(0))
    auth = _make_auth()
    request = httpx.Request(
        "POST",
        "https://cloudaz.example.com/dpc/authorization/pdp",
    )

    flow = auth.auth_flow(request)
    next(flow)
    flow.send(_make_token_response(access_token="token-v1"))
    reauth_req = flow.send(httpx.Response(401, request=request))

    assert str(reauth_req.url) == TOKEN_URL

    retry_req = flow.send(_make_token_response(access_token="token-v2"))

    assert retry_req.headers["Authorization"] == "Bearer token-v2"


def test_token_acquisition_failure_raises() -> None:
    when(time).monotonic().thenReturn(float(0))
    auth = _make_auth()
    request = httpx.Request(
        "POST",
        "https://cloudaz.example.com/dpc/authorization/pdp",
    )

    flow = auth.auth_flow(request)
    next(flow)

    with pytest.raises(exceptions.AuthenticationError) as exc_info:
        flow.send(
            httpx.Response(
                400,
                text="invalid_client",
                request=httpx.Request("POST", TOKEN_URL),
            ),
        )

    assert exc_info.value.status_code == 400


def test_client_credentials_grant_type_in_token_request() -> None:
    when(time).monotonic().thenReturn(float(0))
    auth = _make_auth()
    request = httpx.Request(
        "POST",
        "https://cloudaz.example.com/dpc/authorization/pdp",
    )

    flow = auth.auth_flow(request)
    token_request = next(flow)

    body = token_request.content.decode()
    assert "grant_type=client_credentials" in body
    assert "client_id=pdp-client" in body
    assert "client_secret=pdp-secret" in body


def test_non_json_200_token_response_raises_authentication_error() -> None:
    when(time).monotonic().thenReturn(float(0))
    auth = _make_auth()
    request = httpx.Request("POST", "https://cloudaz.example.com/dpc/authorization/pdp")

    flow = auth.auth_flow(request)
    next(flow)

    with pytest.raises(exceptions.AuthenticationError) as exc_info:
        flow.send(
            httpx.Response(
                200,
                content=b"not-json",
                request=httpx.Request("POST", TOKEN_URL),
            ),
        )

    assert "Invalid JSON response" in exc_info.value.message


def test_token_response_missing_access_token_raises_authentication_error() -> None:
    when(time).monotonic().thenReturn(float(0))
    auth = _make_auth()
    request = httpx.Request("POST", "https://cloudaz.example.com/dpc/authorization/pdp")

    flow = auth.auth_flow(request)
    next(flow)

    with pytest.raises(exceptions.AuthenticationError) as exc_info:
        flow.send(
            httpx.Response(
                200,
                json={"expires_in": 3600},
                request=httpx.Request("POST", TOKEN_URL),
            ),
        )

    assert "missing 'access_token'" in exc_info.value.message
