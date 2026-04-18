from __future__ import annotations

import asyncio
import time
import typing

import httpx
import pytest

from mockito import mock, when

from nextlabs_sdk import _http_transport
from nextlabs_sdk._config import HttpConfig
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


@pytest.mark.parametrize(
    "fail_status",
    [
        pytest.param(503, id="503"),
        pytest.param(500, id="500"),
        pytest.param(429, id="429"),
    ],
)
def test_retries_on_retryable_status_then_succeeds(fail_status: int) -> None:
    request = _make_request()
    fail_resp = _make_response(fail_status, request)
    ok_resp = _make_response(200, request)
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenReturn(fail_resp).thenReturn(ok_resp)
    when(time).sleep(...).thenReturn(None)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=3)
    response = transport.handle_request(request)

    assert response.status_code == 200


@pytest.mark.parametrize(
    "status",
    [pytest.param(400, id="400"), pytest.param(404, id="404")],
)
def test_does_not_retry_on_non_retryable_status(status: int) -> None:
    request = _make_request()
    resp = _make_response(status, request)
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenReturn(resp)

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=3)
    response = transport.handle_request(request)

    assert response.status_code == status


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


def test_clamps_retry_after_to_max_delay() -> None:
    request = _make_request()
    fail_resp = _make_response(429, request, headers={"retry-after": "999"})
    ok_resp = _make_response(200, request)
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenReturn(fail_resp).thenReturn(ok_resp)

    sleep_values: list[float] = []
    when(time).sleep(...).thenAnswer(lambda delay: sleep_values.append(delay))

    transport = _http_transport.RetryTransport(
        wrapped=wrapped, max_retries=3, max_delay=10.0
    )
    response = transport.handle_request(request)

    assert response.status_code == 200
    assert sleep_values[0] == pytest.approx(10.0)


def test_negative_retry_after_clamped_to_zero_sync() -> None:
    request = _make_request()
    fail_resp = _make_response(429, request, headers={"retry-after": "-1"})
    ok_resp = _make_response(200, request)
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenReturn(fail_resp).thenReturn(ok_resp)

    sleep_values: list[float] = []
    when(time).sleep(...).thenAnswer(lambda delay: sleep_values.append(delay))

    transport = _http_transport.RetryTransport(wrapped=wrapped, max_retries=3)
    response = transport.handle_request(request)

    assert response.status_code == 200
    assert sleep_values[0] == pytest.approx(0)


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


def test_async_clamps_retry_after_to_max_delay() -> None:
    request = _make_request()
    fail_resp = _make_response(429, request, headers={"retry-after": "999"})
    ok_resp = _make_response(200, request)
    wrapped = mock(httpx.AsyncBaseTransport)
    when(wrapped).handle_async_request(request).thenReturn(fail_resp).thenReturn(
        ok_resp
    )

    sleep_values: list[float] = []

    def _capture(delay: float) -> _ResolvedAwaitable:
        sleep_values.append(delay)
        return _ResolvedAwaitable()

    when(asyncio).sleep(...).thenAnswer(_capture)

    transport = _http_transport.AsyncRetryTransport(
        wrapped=wrapped, max_retries=3, max_delay=10.0
    )
    response = asyncio.run(transport.handle_async_request(request))

    assert response.status_code == 200
    assert sleep_values[0] == pytest.approx(10.0)


def test_async_negative_retry_after_clamped_to_zero() -> None:
    request = _make_request()
    fail_resp = _make_response(429, request, headers={"retry-after": "-1"})
    ok_resp = _make_response(200, request)
    wrapped = mock(httpx.AsyncBaseTransport)
    when(wrapped).handle_async_request(request).thenReturn(fail_resp).thenReturn(
        ok_resp
    )

    sleep_values: list[float] = []

    def _capture(delay: float) -> _ResolvedAwaitable:
        sleep_values.append(delay)
        return _ResolvedAwaitable()

    when(asyncio).sleep(...).thenAnswer(_capture)

    transport = _http_transport.AsyncRetryTransport(wrapped=wrapped, max_retries=3)
    response = asyncio.run(transport.handle_async_request(request))

    assert response.status_code == 200
    assert sleep_values[0] == pytest.approx(0)


# ── Factory tests ──


def test_create_http_client_returns_configured_client() -> None:
    auth = mock(httpx.Auth)
    client = _http_transport.create_http_client(
        base_url="https://api.example.com",
        auth=auth,
        http_config=HttpConfig(timeout=15.0),
    )
    assert str(client.base_url) == "https://api.example.com"
    assert client.timeout == httpx.Timeout(15.0)
    client.close()


def test_create_async_http_client_returns_configured_client() -> None:
    auth = mock(httpx.Auth)
    client = _http_transport.create_async_http_client(
        base_url="https://api.example.com",
        auth=auth,
        http_config=HttpConfig(timeout=15.0),
    )
    assert str(client.base_url) == "https://api.example.com"
    assert client.timeout == httpx.Timeout(15.0)
    asyncio.run(client.aclose())


# ── Redirect handling tests ──


class _NoopAuth(httpx.Auth):
    def auth_flow(
        self,
        request: httpx.Request,
    ) -> "typing.Generator[httpx.Request, httpx.Response, None]":
        yield request


def _redirect_handler(
    location: str,
    final_content: bytes = b'{"ok": true}',
    final_content_type: str = "application/json",
    final_status: int = 200,
):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"location": location})
        return httpx.Response(
            final_status,
            content=final_content,
            headers={"content-type": final_content_type},
        )

    return handler


def _build_sync_factory_client_with_transport(
    transport: httpx.MockTransport,
) -> httpx.Client:
    factory_client = _http_transport.create_http_client(
        base_url="https://api.example.com",
        auth=_NoopAuth(),
    )
    factory_client._transport = transport
    return factory_client


def _build_async_factory_client_with_transport(
    transport: httpx.MockTransport,
) -> httpx.AsyncClient:
    factory_client = _http_transport.create_async_http_client(
        base_url="https://api.example.com",
        auth=_NoopAuth(),
    )
    factory_client._transport = transport
    return factory_client


def test_sync_client_follows_redirect_to_json() -> None:
    mock_transport = httpx.MockTransport(
        _redirect_handler("https://api.example.com/final"),
    )
    client = _build_sync_factory_client_with_transport(mock_transport)
    try:
        response = client.get("/redirect")
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
    finally:
        client.close()


def test_async_client_follows_redirect_to_json() -> None:
    mock_transport = httpx.MockTransport(
        _redirect_handler("https://api.example.com/final"),
    )
    client = _build_async_factory_client_with_transport(mock_transport)

    async def run() -> httpx.Response:
        try:
            return await client.get("/redirect")
        finally:
            await client.aclose()

    response = asyncio.run(run())
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(response.history) == 1


def test_sync_client_redirect_loop_raises_transport_error() -> None:
    def loop_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"location": "https://api.example.com/redirect"},
        )

    client = _build_sync_factory_client_with_transport(
        httpx.MockTransport(loop_handler),
    )
    try:
        with pytest.raises(TransportError) as exc_info:
            client.get("/redirect")
    finally:
        client.close()

    assert exc_info.value.request_method == "GET"
    assert "redirect" in (exc_info.value.request_url or "")
    assert isinstance(exc_info.value.__cause__, httpx.TooManyRedirects)


def test_async_client_redirect_loop_raises_transport_error() -> None:
    def loop_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"location": "https://api.example.com/redirect"},
        )

    client = _build_async_factory_client_with_transport(
        httpx.MockTransport(loop_handler),
    )

    async def run() -> None:
        try:
            await client.get("/redirect")
        finally:
            await client.aclose()

    with pytest.raises(TransportError) as exc_info:
        asyncio.run(run())

    assert isinstance(exc_info.value.__cause__, httpx.TooManyRedirects)
