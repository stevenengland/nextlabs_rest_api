from __future__ import annotations

import asyncio
import logging

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._http_transport_logging import LoggingTransport
from nextlabs_sdk._http_transport_logging_async import AsyncLoggingTransport


def _capture_debug(
    caplog: pytest.LogCaptureFixture,
) -> list[str]:
    return [record.getMessage() for record in caplog.records]


def test_sync_logging_transport_emits_request_and_response_lines(
    caplog: pytest.LogCaptureFixture,
) -> None:
    request = httpx.Request("GET", "https://api.example.com/x")
    response = httpx.Response(200, request=request, content=b"ok")
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenReturn(response)

    transport = LoggingTransport(wrapped=wrapped)
    with caplog.at_level(logging.DEBUG, logger="nextlabs_sdk"):
        result = transport.handle_request(request)

    assert result is response
    messages = _capture_debug(caplog)
    assert any(msg.startswith("→ GET ") for msg in messages)
    assert any(msg.startswith("← 200") for msg in messages)


def test_sync_logging_transport_reraises_inner_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    request = httpx.Request("GET", "https://api.example.com/x")
    wrapped = mock(httpx.BaseTransport)
    boom = httpx.ConnectError("down")
    when(wrapped).handle_request(request).thenRaise(boom)

    transport = LoggingTransport(wrapped=wrapped)
    with caplog.at_level(logging.DEBUG, logger="nextlabs_sdk"):
        with pytest.raises(httpx.ConnectError):
            transport.handle_request(request)

    messages = _capture_debug(caplog)
    assert any(msg.startswith("→ GET ") for msg in messages)
    assert any("transport error" in msg for msg in messages)


def test_sync_logging_transport_redacts_authorization_header(
    caplog: pytest.LogCaptureFixture,
) -> None:
    request = httpx.Request(
        "GET",
        "https://api.example.com/x",
        headers={"Authorization": "Bearer secret-token-abc"},
    )
    response = httpx.Response(200, request=request, content=b"ok")
    wrapped = mock(httpx.BaseTransport)
    when(wrapped).handle_request(request).thenReturn(response)

    transport = LoggingTransport(wrapped=wrapped)
    with caplog.at_level(logging.DEBUG, logger="nextlabs_sdk"):
        transport.handle_request(request)

    joined = "\n".join(_capture_debug(caplog))
    assert "secret-token-abc" not in joined
    assert "Bearer ***" in joined


class _FakeAsync(httpx.AsyncBaseTransport):
    async def handle_async_request(
        self,
        request: httpx.Request,
    ) -> httpx.Response:
        return self._response  # type: ignore[attr-defined]


class _BoomTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(
        self,
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ConnectError("down")


def test_async_logging_transport_emits_request_and_response_lines(
    caplog: pytest.LogCaptureFixture,
) -> None:
    request = httpx.Request("POST", "https://api.example.com/x")
    response = httpx.Response(201, request=request, content=b"done")
    inner = _FakeAsync()
    inner._response = response  # type: ignore[attr-defined]

    transport = AsyncLoggingTransport(wrapped=inner)
    with caplog.at_level(logging.DEBUG, logger="nextlabs_sdk"):
        result = asyncio.run(transport.handle_async_request(request))

    assert result is response
    messages = _capture_debug(caplog)
    assert any(msg.startswith("→ POST ") for msg in messages)
    assert any(msg.startswith("← 201") for msg in messages)


def test_async_logging_transport_reraises_inner_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    request = httpx.Request("GET", "https://api.example.com/x")

    transport = AsyncLoggingTransport(wrapped=_BoomTransport())
    with caplog.at_level(logging.DEBUG, logger="nextlabs_sdk"):
        with pytest.raises(httpx.ConnectError):
            asyncio.run(transport.handle_async_request(request))

    messages = _capture_debug(caplog)
    assert any("transport error" in msg for msg in messages)
