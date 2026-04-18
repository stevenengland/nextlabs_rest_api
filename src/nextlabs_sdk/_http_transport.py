from __future__ import annotations

import asyncio as _asyncio
import logging
import time

import httpx

from nextlabs_sdk._config import HttpConfig
from nextlabs_sdk._retry_policy import RetryPolicy
from nextlabs_sdk.exceptions import (
    NextLabsError,
    RequestTimeoutError,
    TransportError,
)

_SSL_VERIFY_MARKER = "CERTIFICATE_VERIFY_FAILED"
_SSL_HINT = (
    "SSL certificate verification failed: {detail}. "
    "Use --no-verify to bypass (dev/self-signed servers only)."
)

logger = logging.getLogger("nextlabs_sdk")

_RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
)


class RetryTransport(httpx.BaseTransport):

    def __init__(
        self,
        wrapped: httpx.BaseTransport,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        self._wrapped = wrapped
        self._policy = RetryPolicy(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
        )

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        last_response: httpx.Response | None = None
        last_exc: BaseException | None = None
        max_retries = self._policy.max_retries

        for attempt in range(max_retries + 1):
            last_response, last_exc = _try_sync_request(self._wrapped, request)

            if last_response is not None and not self._policy.should_retry(
                last_response, last_exc
            ):
                return last_response

            if attempt < max_retries:
                delay = self._policy.next_delay(attempt, last_response, last_exc)
                _log_retry(
                    max_retries,
                    attempt,
                    delay,
                    error=last_exc,
                    status_code=(last_response.status_code if last_response else None),
                )
                time.sleep(delay)

        return _resolve_final(last_exc, last_response, request)

    def close(self) -> None:
        self._wrapped.close()


class AsyncRetryTransport(httpx.AsyncBaseTransport):

    def __init__(
        self,
        wrapped: httpx.AsyncBaseTransport,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        self._wrapped = wrapped
        self._policy = RetryPolicy(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        last_response: httpx.Response | None = None
        last_exc: BaseException | None = None
        max_retries = self._policy.max_retries
        attempt = 0

        while attempt <= max_retries:
            last_response, last_exc = await _try_async_request(self._wrapped, request)

            if last_response is not None and not self._policy.should_retry(
                last_response, last_exc
            ):
                return last_response

            if attempt < max_retries:
                delay = self._policy.next_delay(attempt, last_response, last_exc)
                _log_retry(
                    max_retries,
                    attempt,
                    delay,
                    error=last_exc,
                    status_code=(last_response.status_code if last_response else None),
                )
                await _asyncio.sleep(delay)

            attempt += 1

        return _resolve_final(last_exc, last_response, request)

    async def aclose(self) -> None:
        await self._wrapped.aclose()


def create_http_client(
    *,
    base_url: str,
    auth: httpx.Auth,
    http_config: HttpConfig | None = None,
) -> httpx.Client:
    effective = http_config or HttpConfig()
    inner: httpx.BaseTransport = httpx.HTTPTransport(verify=effective.verify_ssl)
    if effective.verbose >= 2:
        from nextlabs_sdk._http_transport_logging import LoggingTransport

        inner = LoggingTransport(wrapped=inner)
    transport = RetryTransport(
        wrapped=inner,
        max_retries=effective.retry.max_retries,
        base_delay=effective.retry.base_delay,
        max_delay=effective.retry.max_delay,
    )
    return _RedirectAwareClient(
        base_url=base_url,
        auth=auth,
        timeout=effective.timeout,
        transport=transport,
        follow_redirects=True,
    )


def create_async_http_client(
    *,
    base_url: str,
    auth: httpx.Auth,
    http_config: HttpConfig | None = None,
) -> httpx.AsyncClient:
    effective = http_config or HttpConfig()
    inner: httpx.AsyncBaseTransport = httpx.AsyncHTTPTransport(
        verify=effective.verify_ssl,
    )
    if effective.verbose >= 2:
        from nextlabs_sdk._http_transport_logging_async import AsyncLoggingTransport

        inner = AsyncLoggingTransport(wrapped=inner)
    transport = AsyncRetryTransport(
        wrapped=inner,
        max_retries=effective.retry.max_retries,
        base_delay=effective.retry.base_delay,
        max_delay=effective.retry.max_delay,
    )
    return _AsyncRedirectAwareClient(
        base_url=base_url,
        auth=auth,
        timeout=effective.timeout,
        transport=transport,
        follow_redirects=True,
    )


class _RedirectAwareClient(httpx.Client):

    def send(self, request: httpx.Request, **kwargs: object) -> httpx.Response:
        try:
            return super().send(request, **kwargs)  # type: ignore[arg-type]
        except httpx.TooManyRedirects as exc:
            raise _wrap_transport_exception(exc, request) from exc


class _AsyncRedirectAwareClient(httpx.AsyncClient):

    async def send(
        self,
        request: httpx.Request,
        **kwargs: object,
    ) -> httpx.Response:
        try:
            return await super().send(request, **kwargs)  # type: ignore[arg-type]
        except httpx.TooManyRedirects as exc:
            raise _wrap_transport_exception(exc, request) from exc


def _try_sync_request(
    wrapped: httpx.BaseTransport,
    request: httpx.Request,
) -> tuple[httpx.Response | None, BaseException | None]:
    try:
        return wrapped.handle_request(request), None
    except _RETRYABLE_EXCEPTIONS as exc:
        return None, exc


async def _try_async_request(
    wrapped: httpx.AsyncBaseTransport,
    request: httpx.Request,
) -> tuple[httpx.Response | None, BaseException | None]:
    try:
        return await wrapped.handle_async_request(request), None
    except _RETRYABLE_EXCEPTIONS as exc:
        return None, exc


def _resolve_final(
    last_exc: BaseException | None,
    last_response: httpx.Response | None,
    request: httpx.Request,
) -> httpx.Response:
    if last_exc is not None:
        raise _wrap_transport_exception(last_exc, request) from last_exc
    if last_response is not None:
        return last_response
    msg = "No request attempts were made"
    raise RuntimeError(msg)


def _wrap_transport_exception(
    exc: BaseException,
    request: httpx.Request,
) -> NextLabsError:
    method = request.method
    url = str(request.url)
    detail = str(exc) or exc.__class__.__name__

    if isinstance(exc, (httpx.ConnectTimeout, httpx.ReadTimeout)):
        return RequestTimeoutError(
            message=f"Request timed out: {detail}",
            request_method=method,
            request_url=url,
        )

    if isinstance(exc, httpx.ConnectError) and _SSL_VERIFY_MARKER in detail:
        return TransportError(
            message=_SSL_HINT.format(detail=detail),
            request_method=method,
            request_url=url,
        )

    if isinstance(exc, httpx.TooManyRedirects):
        return TransportError(
            message=f"Too many redirects: {detail}",
            request_method=method,
            request_url=url,
        )

    return TransportError(
        message=f"Connection error: {detail}",
        request_method=method,
        request_url=url,
    )


def _log_retry(
    max_retries: int,
    attempt: int,
    delay: float,
    error: BaseException | None = None,
    status_code: int | None = None,
) -> None:
    reason = f"HTTP {status_code}" if status_code else str(error)
    logger.debug(
        "Retry %d/%d after %.1fs (%s)",
        attempt + 1,
        max_retries,
        delay,
        reason,
    )
