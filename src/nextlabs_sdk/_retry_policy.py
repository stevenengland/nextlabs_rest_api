from __future__ import annotations

import math
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
)

_RETRYABLE_STATUS_FLOOR = 500
_RATE_LIMIT_STATUS = 429
_BACKOFF_BASE = 2
_NO_DELAY: float = 0
_RNG = random.SystemRandom()


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


class RetryPolicy:
    """Encapsulates retry decisions and delay computation.

    All invariants for the next-delay value live here so that retry-loop
    consumers cannot accidentally pass an unbounded or negative value to
    ``time.sleep`` / ``asyncio.sleep``.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def should_retry(
        self,
        response: httpx.Response | None,
        error: BaseException | None,
    ) -> bool:
        if error is not None:
            return isinstance(error, _RETRYABLE_EXCEPTIONS)
        if response is None:
            return False
        status = response.status_code
        return status == _RATE_LIMIT_STATUS or status >= _RETRYABLE_STATUS_FLOOR

    def next_delay(
        self,
        attempt: int,
        response: httpx.Response | None,
        error: BaseException | None,
    ) -> float:
        if error is not None and response is None:
            return self._backoff_delay(attempt)
        if response is not None:
            parsed = self._parse_retry_after(response)
            if parsed is not None:
                lower_bound: float = 0
                return max(lower_bound, min(parsed, self._max_delay))
        return self._backoff_delay(attempt)

    def _parse_retry_after(self, response: httpx.Response) -> float | None:
        header = response.headers.get("retry-after")
        if header is None:
            return None
        parsed_value = _parse_delay_seconds(header)
        if parsed_value is None:
            parsed_value = _parse_http_date_seconds(header)
        if parsed_value is None or not math.isfinite(parsed_value):
            return None
        return parsed_value

    def _backoff_delay(self, attempt: int) -> float:
        exp_delay = min(self._base_delay * (_BACKOFF_BASE**attempt), self._max_delay)
        return _RNG.uniform(0, exp_delay)


def _parse_delay_seconds(header: str) -> float | None:
    try:
        return float(header)
    except ValueError:
        return None


def _parse_http_date_seconds(header: str) -> float | None:
    """Parse an RFC 7231 HTTP-date and return seconds until that instant.

    Returns ``None`` for malformed dates so the caller can fall back to
    exponential backoff. Past dates are clamped to ``0`` per RFC 7231 §7.1.3.
    """
    try:
        target = parsedate_to_datetime(header)
    except (TypeError, ValueError):
        return None
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    return max(_NO_DELAY, (target - _now_utc()).total_seconds())
