from __future__ import annotations

import contextlib
import time

import httpx

from nextlabs_sdk._http_transport_logging import (
    _log_failure_safely,
    _log_request_safely,
    _log_response_safely,
)


class AsyncLoggingTransport(httpx.AsyncBaseTransport):
    """Async twin of :class:`LoggingTransport`."""

    def __init__(self, wrapped: httpx.AsyncBaseTransport) -> None:
        self._wrapped = wrapped

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        _log_request_safely(request)
        start = time.perf_counter()
        try:
            response = await self._wrapped.handle_async_request(request)
        except BaseException:
            _log_failure_safely(time.perf_counter() - start)
            raise
        with contextlib.suppress(Exception):
            await response.aread()
        _log_response_safely(response, time.perf_counter() - start)
        return response

    async def aclose(self) -> None:
        await self._wrapped.aclose()
