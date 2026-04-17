from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from mockito import mock, when

from nextlabs_sdk import _http_transport
from nextlabs_sdk.exceptions import RequestTimeoutError, TransportError


def _make_request() -> httpx.Request:
    return httpx.Request("GET", "https://example.com/api")


def _make_response(
    status_code: int,
    request: httpx.Request,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return httpx.Response(status_code, request=request, headers=headers)


# ── Sync RetryTransport tests ──


def test_successful_request_returns_immediately() -> None:
    request = _make_request()
    expected = _make_response(200, request)
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenReturn(expected)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=3)
    response = transport.handle_request(request)

    assert response.status_code == 200


def test_retries_on_503_then_succeeds() -> None:
    request = _make_request()
    fail_resp = _make_response(503, request)
    ok_resp = _make_response(200, request)
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenReturn(fail_resp).thenReturn(ok_resp)
    when(time).sleep(...).thenReturn(None)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=3)
    response = transport.handle_request(request)

    assert response.status_code == 200


def test_retries_on_500_then_succeeds() -> None:
    request = _make_request()
    fail_resp = _make_response(500, request)
    ok_resp = _make_response(200, request)
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenReturn(fail_resp).thenReturn(ok_resp)
    when(time).sleep(...).thenReturn(None)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=3)
    response = transport.handle_request(request)

    assert response.status_code == 200


def test_retries_on_429_then_succeeds() -> None:
    request = _make_request()
    fail_resp = _make_response(429, request)
    ok_resp = _make_response(200, request)
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenReturn(fail_resp).thenReturn(ok_resp)
    when(time).sleep(...).thenReturn(None)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=3)
    response = transport.handle_request(request)

    assert response.status_code == 200


def test_does_not_retry_on_400() -> None:
    request = _make_request()
    resp = _make_response(400, request)
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenReturn(resp)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=3)
    response = transport.handle_request(request)

    assert response.status_code == 400


def test_does_not_retry_on_404() -> None:
    request = _make_request()
    resp = _make_response(404, request)
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenReturn(resp)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=3)
    response = transport.handle_request(request)

    assert response.status_code == 404


def test_returns_last_response_when_retries_exhausted() -> None:
    request = _make_request()
    fail_resp = _make_response(503, request)
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenReturn(fail_resp)
    when(time).sleep(...).thenReturn(None)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=2)
    response = transport.handle_request(request)

    assert response.status_code == 503


def test_retries_on_connect_error_then_succeeds() -> None:
    request = _make_request()
    ok_resp = _make_response(200, request)
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenRaise(
        httpx.ConnectError("connection refused"),
    ).thenReturn(ok_resp)
    when(time).sleep(...).thenReturn(None)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=3)
    response = transport.handle_request(request)

    assert response.status_code == 200


def test_raises_transport_error_when_retries_exhausted() -> None:
    request = _make_request()
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenRaise(
        httpx.ConnectError("connection refused"),
    )
    when(time).sleep(...).thenReturn(None)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=2)
    with pytest.raises(TransportError) as exc_info:
        transport.handle_request(request)

    assert "Connection error" in exc_info.value.message
    assert "connection refused" in exc_info.value.message
    assert exc_info.value.request_method == "GET"
    assert exc_info.value.request_url == "https://example.com/api"
    assert isinstance(exc_info.value.__cause__, httpx.ConnectError)


def test_raises_transport_error_with_ssl_hint_on_verify_failure() -> None:
    request = _make_request()
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenRaise(
        httpx.ConnectError(
            "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
            "self-signed certificate (_ssl.c:1010)",
        ),
    )
    when(time).sleep(...).thenReturn(None)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=1)
    with pytest.raises(TransportError) as exc_info:
        transport.handle_request(request)

    assert "SSL certificate verification failed" in exc_info.value.message
    assert "--no-verify" in exc_info.value.message


def test_raises_request_timeout_error_on_connect_timeout_exhausted() -> None:
    request = _make_request()
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenRaise(
        httpx.ConnectTimeout("connect timed out"),
    )
    when(time).sleep(...).thenReturn(None)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=1)
    with pytest.raises(RequestTimeoutError) as exc_info:
        transport.handle_request(request)

    assert "Request timed out" in exc_info.value.message
    assert "connect timed out" in exc_info.value.message


def test_raises_request_timeout_error_on_read_timeout_exhausted() -> None:
    request = _make_request()
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenRaise(
        httpx.ReadTimeout("read timed out"),
    )
    when(time).sleep(...).thenReturn(None)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=1)
    with pytest.raises(RequestTimeoutError):
        transport.handle_request(request)


def test_retries_on_read_timeout_then_succeeds() -> None:
    request = _make_request()
    ok_resp = _make_response(200, request)
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenRaise(
        httpx.ReadTimeout("read timed out"),
    ).thenReturn(ok_resp)
    when(time).sleep(...).thenReturn(None)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=3)
    response = transport.handle_request(request)

    assert response.status_code == 200


def test_no_retry_when_max_retries_zero() -> None:
    request = _make_request()
    resp = _make_response(503, request)
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenReturn(resp)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=0)
    response = transport.handle_request(request)

    assert response.status_code == 503


def test_respects_retry_after_header() -> None:
    request = _make_request()
    fail_resp = _make_response(429, request, headers={"retry-after": "5"})
    ok_resp = _make_response(200, request)
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenReturn(fail_resp).thenReturn(ok_resp)

    sleep_values: list[float] = []
    when(time).sleep(...).thenAnswer(lambda delay: sleep_values.append(delay))

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=3)
    response = transport.handle_request(request)

    assert response.status_code == 200
    assert sleep_values[0] == pytest.approx(5.0)


# ── Async AsyncRetryTransport tests ──


class _ResolvedAwaitable:
    """Lightweight awaitable that resolves immediately without coroutine warnings."""

    def __await__(self):
        return iter(())


def test_async_retry_succeeds_after_transient_failure() -> None:
    request = _make_request()
    fail_resp = _make_response(503, request)
    ok_resp = _make_response(200, request)
    wrapped = mock(httpx.AsyncBaseTransport)
    when(wrapped).handle_async_request(request).thenReturn(fail_resp).thenReturn(
        ok_resp
    )
    when(asyncio).sleep(...).thenAnswer(lambda *args: _ResolvedAwaitable())

    transport = _http_transport.AsyncRetryTransport(wrapped=wrapped, max_retries=3)
    response = asyncio.run(transport.handle_async_request(request))

    assert response.status_code == 200


def test_async_retry_raises_transport_error_on_exhausted_connect_errors() -> None:
    request = _make_request()
    wrapped = mock(httpx.AsyncBaseTransport)
    when(wrapped).handle_async_request(request).thenRaise(
        httpx.ConnectError("connection refused"),
    )
    when(asyncio).sleep(...).thenAnswer(lambda *args: _ResolvedAwaitable())

    transport = _http_transport.AsyncRetryTransport(wrapped=wrapped, max_retries=2)
    with pytest.raises(TransportError) as exc_info:
        asyncio.run(transport.handle_async_request(request))

    assert "Connection error" in exc_info.value.message


def test_async_retry_raises_transport_error_with_ssl_hint() -> None:
    request = _make_request()
    wrapped = mock(httpx.AsyncBaseTransport)
    when(wrapped).handle_async_request(request).thenRaise(
        httpx.ConnectError(
            "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed",
        ),
    )
    when(asyncio).sleep(...).thenAnswer(lambda *args: _ResolvedAwaitable())

    transport = _http_transport.AsyncRetryTransport(wrapped=wrapped, max_retries=1)
    with pytest.raises(TransportError) as exc_info:
        asyncio.run(transport.handle_async_request(request))

    assert "SSL certificate verification failed" in exc_info.value.message
    assert "--no-verify" in exc_info.value.message


def test_async_retry_raises_request_timeout_error_on_read_timeout() -> None:
    request = _make_request()
    wrapped = mock(httpx.AsyncBaseTransport)
    when(wrapped).handle_async_request(request).thenRaise(
        httpx.ReadTimeout("read timed out"),
    )
    when(asyncio).sleep(...).thenAnswer(lambda *args: _ResolvedAwaitable())

    transport = _http_transport.AsyncRetryTransport(wrapped=wrapped, max_retries=1)
    with pytest.raises(RequestTimeoutError):
        asyncio.run(transport.handle_async_request(request))


# ── Factory tests ──


def test_create_http_client_returns_configured_client() -> None:
    auth = mock(httpx.Auth)
    client = _http_transport.create_http_client(
        base_url="https://api.example.com",
        auth=auth,
        timeout=15.0,
    )
    assert str(client.base_url) == "https://api.example.com"
    assert client.timeout == httpx.Timeout(15.0)
    client.close()


def test_create_async_http_client_returns_configured_client() -> None:
    auth = mock(httpx.Auth)
    client = _http_transport.create_async_http_client(
        base_url="https://api.example.com",
        auth=auth,
        timeout=15.0,
    )
    assert str(client.base_url) == "https://api.example.com"
    assert client.timeout == httpx.Timeout(15.0)
    asyncio.run(client.aclose())
