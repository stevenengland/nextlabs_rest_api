from __future__ import annotations

import contextlib
import time

import httpx

from nextlabs_sdk._logging import (
    format_request_line,
    format_response_line,
    logger,
    redact_body,
    redact_headers,
    truncate,
)


def _log_request_safely(request: httpx.Request) -> None:
    with contextlib.suppress(Exception):
        logger.debug(format_request_line(request))
        logger.debug("    headers: %s", redact_headers(request.headers))
        body = redact_body(request.headers.get("content-type"), request.content)
        logger.debug("    body:    %s", truncate(body))


def _log_response_safely(response: httpx.Response, elapsed: float) -> None:
    with contextlib.suppress(Exception):
        logger.debug(format_response_line(response, elapsed))
        body = redact_body(response.headers.get("content-type"), response.content)
        logger.debug("    body:    %s", truncate(body))


def _log_failure_safely(elapsed: float) -> None:
    with contextlib.suppress(Exception):
        logger.debug("← transport error after %.3fs", elapsed)


class LoggingTransport(httpx.BaseTransport):
    """Wraps a transport and logs every request/response at DEBUG.

    Redacts sensitive headers and body fields. Logging failures never
    prevent the request from executing.
    """

    def __init__(self, wrapped: httpx.BaseTransport) -> None:
        self._wrapped = wrapped

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        _log_request_safely(request)
        start = time.perf_counter()
        try:
            response = self._wrapped.handle_request(request)
        except BaseException:
            _log_failure_safely(time.perf_counter() - start)
            raise
        response.read()
        _log_response_safely(response, time.perf_counter() - start)
        return response

    def close(self) -> None:
        self._wrapped.close()
