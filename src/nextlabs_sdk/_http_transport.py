from __future__ import annotations

import asyncio as _asyncio
import logging
import random
import time

import httpx

from nextlabs_sdk._config import RetryConfig

logger = logging.getLogger("nextlabs_sdk")

_RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
)

_RETRYABLE_STATUS_FLOOR = 500
_RATE_LIMIT_STATUS = 429
_RNG = random.SystemRandom()
_BACKOFF_BASE = 2


class RetryTransport(httpx.BaseTransport):

    def __init__(
        self,
        wrapped: httpx.BaseTransport,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        self._wrapped = wrapped
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        last_response: httpx.Response | None = None
        last_exc: BaseException | None = None

        for attempt in range(self._max_retries + 1):
            last_response, last_exc = _try_sync_request(self._wrapped, request)

            if last_response is not None and not _needs_retry(last_response, last_exc):
                return last_response

            if attempt < self._max_retries:
                self._sleep_before_retry(attempt, last_response, last_exc)

        return _resolve_final(last_exc, last_response)

    def close(self) -> None:
        self._wrapped.close()

    def _sleep_before_retry(
        self,
        attempt: int,
        response: httpx.Response | None,
        error: BaseException | None,
    ) -> None:
        if response is None:
            delay = _calculate_delay(self._base_delay, self._max_delay, attempt)
            _log_retry(self._max_retries, attempt, delay, error=error)
        else:
            delay = _get_retry_delay(response, self._base_delay, self._max_delay, attempt)
            _log_retry(self._max_retries, attempt, delay, status_code=response.status_code)
        time.sleep(delay)


class AsyncRetryTransport(httpx.AsyncBaseTransport):

    def __init__(
        self,
        wrapped: httpx.AsyncBaseTransport,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        self._wrapped = wrapped
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        last_response: httpx.Response | None = None
        last_exc: BaseException | None = None
        attempt = 0

        while attempt <= self._max_retries:
            last_response, last_exc = await _try_async_request(self._wrapped, request)

            if last_response is not None and not _needs_retry(last_response, last_exc):
                return last_response

            if attempt < self._max_retries:
                await self._sleep_before_retry(attempt, last_response, last_exc)

            attempt += 1

        return _resolve_final(last_exc, last_response)

    async def aclose(self) -> None:
        await self._wrapped.aclose()

    async def _sleep_before_retry(
        self,
        attempt: int,
        response: httpx.Response | None,
        error: BaseException | None,
    ) -> None:
        if response is None:
            delay = _calculate_delay(self._base_delay, self._max_delay, attempt)
            _log_retry(self._max_retries, attempt, delay, error=error)
        else:
            delay = _get_retry_delay(response, self._base_delay, self._max_delay, attempt)
            _log_retry(self._max_retries, attempt, delay, status_code=response.status_code)
        await _asyncio.sleep(delay)


def create_http_client(
    *,
    base_url: str,
    auth: httpx.Auth,
    timeout: float = 30.0,
    verify_ssl: bool = True,
    retry: RetryConfig | None = None,
) -> httpx.Client:
    effective_retry = retry or RetryConfig()
    transport = RetryTransport(
        wrapped=httpx.HTTPTransport(verify=verify_ssl),
        max_retries=effective_retry.max_retries,
        base_delay=effective_retry.base_delay,
        max_delay=effective_retry.max_delay,
    )
    return httpx.Client(
        base_url=base_url,
        auth=auth,
        timeout=timeout,
        transport=transport,
    )


def create_async_http_client(
    *,
    base_url: str,
    auth: httpx.Auth,
    timeout: float = 30.0,
    verify_ssl: bool = True,
    retry: RetryConfig | None = None,
) -> httpx.AsyncClient:
    effective_retry = retry or RetryConfig()
    transport = AsyncRetryTransport(
        wrapped=httpx.AsyncHTTPTransport(verify=verify_ssl),
        max_retries=effective_retry.max_retries,
        base_delay=effective_retry.base_delay,
        max_delay=effective_retry.max_delay,
    )
    return httpx.AsyncClient(
        base_url=base_url,
        auth=auth,
        timeout=timeout,
        transport=transport,
    )


def _needs_retry(
    response: httpx.Response | None,
    error: BaseException | None,
) -> bool:
    if error is not None:
        return True
    if response is None:
        return False
    return _is_retryable_status(response.status_code)


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
) -> httpx.Response:
    if last_exc is not None:
        raise last_exc
    if last_response is not None:
        return last_response
    msg = "No request attempts were made"
    raise RuntimeError(msg)


def _is_retryable_status(status_code: int) -> bool:
    return (
        status_code == _RATE_LIMIT_STATUS
        or status_code >= _RETRYABLE_STATUS_FLOOR
    )


def _calculate_delay(base_delay: float, max_delay: float, attempt: int) -> float:
    exp_delay = min(base_delay * (_BACKOFF_BASE ** attempt), max_delay)
    return _RNG.uniform(0, exp_delay)


def _get_retry_delay(
    response: httpx.Response,
    base_delay: float,
    max_delay: float,
    attempt: int,
) -> float:
    retry_after = response.headers.get("retry-after")
    if retry_after is not None:
        try:
            return float(retry_after)
        except ValueError:
            return _calculate_delay(base_delay, max_delay, attempt)
    return _calculate_delay(base_delay, max_delay, attempt)


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
