from __future__ import annotations

import math

import httpx
import pytest

from hypothesis import given, settings
from hypothesis import strategies as st

from nextlabs_sdk._retry_policy import RetryPolicy

_MAX_DELAY = 10.0
_SMALL_MAX_DELAY = 5.0


def _assert_within_bounds(delay: float, upper: float) -> None:
    assert delay >= 0
    assert delay <= upper


def _make_response(
    status_code: int,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    request = httpx.Request("GET", "https://example.com/api")
    return httpx.Response(status_code, request=request, headers=headers)


# ── next_delay: Retry-After honoured when sane ──


def test_numeric_retry_after_within_bounds_returned_as_is() -> None:
    policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=30.0)
    response = _make_response(429, headers={"retry-after": "5"})

    assert policy.next_delay(0, response, None) == pytest.approx(5.0)


def test_zero_retry_after_returns_zero() -> None:
    policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=30.0)
    response = _make_response(429, headers={"retry-after": "0"})

    assert policy.next_delay(0, response, None) == pytest.approx(0)


# ── next_delay: invariants enforced ──


def test_negative_retry_after_clamped_to_zero() -> None:
    policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=30.0)
    response = _make_response(429, headers={"retry-after": "-1"})

    assert policy.next_delay(0, response, None) == pytest.approx(0)


def test_retry_after_greater_than_max_delay_clamped_to_max() -> None:
    policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=_MAX_DELAY)
    response = _make_response(429, headers={"retry-after": "999"})

    assert policy.next_delay(0, response, None) == pytest.approx(10)


def test_huge_retry_after_does_not_stall() -> None:
    policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=30.0)
    response = _make_response(429, headers={"retry-after": "99999999999"})

    assert policy.next_delay(0, response, None) == pytest.approx(30)


# ── next_delay: fall through to backoff ──


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_non_finite_retry_after_falls_through_to_backoff(value: str) -> None:
    policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=_MAX_DELAY)
    response = _make_response(429, headers={"retry-after": value})

    delay = policy.next_delay(0, response, None)

    _assert_within_bounds(delay, _MAX_DELAY)


def test_unparseable_retry_after_falls_through_to_backoff() -> None:
    policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=_MAX_DELAY)
    response = _make_response(429, headers={"retry-after": "not-a-number"})

    delay = policy.next_delay(0, response, None)

    _assert_within_bounds(delay, _MAX_DELAY)


def test_missing_retry_after_uses_backoff() -> None:
    policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=_MAX_DELAY)
    response = _make_response(503)

    delay = policy.next_delay(0, response, None)

    _assert_within_bounds(delay, _MAX_DELAY)


def test_no_response_uses_backoff() -> None:
    policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=_MAX_DELAY)

    delay = policy.next_delay(0, None, httpx.ConnectError("boom"))

    _assert_within_bounds(delay, _MAX_DELAY)


# ── next_delay: backoff growth bounded ──


def test_backoff_never_exceeds_max_delay() -> None:
    policy = RetryPolicy(max_retries=10, base_delay=1.0, max_delay=_SMALL_MAX_DELAY)
    for attempt in range(10):
        delay = policy.next_delay(attempt, None, httpx.ConnectError("boom"))
        _assert_within_bounds(delay, _SMALL_MAX_DELAY)


# ── Hypothesis property test (issue #13) ──


@settings(max_examples=200)
@given(
    retry_after=st.floats(
        min_value=-1e6, max_value=1e12, allow_nan=False, allow_infinity=False
    ),
    base_delay=st.floats(min_value=0.01, max_value=5.0, allow_nan=False),
    max_delay=st.floats(min_value=0.01, max_value=60.0, allow_nan=False),
    attempt=st.integers(min_value=0, max_value=5),
)
def test_next_delay_is_non_negative_and_bounded(
    retry_after: float,
    base_delay: float,
    max_delay: float,
    attempt: int,
) -> None:
    policy = RetryPolicy(max_retries=10, base_delay=base_delay, max_delay=max_delay)
    response = _make_response(429, headers={"retry-after": str(retry_after)})

    delay = policy.next_delay(attempt, response, None)

    _assert_within_bounds(delay, max_delay)
    assert math.isfinite(delay)


@settings(max_examples=100)
@given(
    base_delay=st.floats(min_value=0.01, max_value=5.0, allow_nan=False),
    max_delay=st.floats(min_value=0.01, max_value=60.0, allow_nan=False),
    attempt=st.integers(min_value=0, max_value=20),
)
def test_backoff_without_header_is_non_negative_and_bounded(
    base_delay: float,
    max_delay: float,
    attempt: int,
) -> None:
    policy = RetryPolicy(max_retries=20, base_delay=base_delay, max_delay=max_delay)

    delay = policy.next_delay(attempt, None, httpx.ConnectError("boom"))

    _assert_within_bounds(delay, max_delay)


# ── should_retry ──


@pytest.mark.parametrize("status", [429, 500, 502, 503, 599])
def test_should_retry_true_for_retryable_status(status: int) -> None:
    policy = RetryPolicy()
    assert policy.should_retry(_make_response(status), None) is True


@pytest.mark.parametrize("status", [200, 301, 400, 401, 404, 499])
def test_should_retry_false_for_non_retryable_status(status: int) -> None:
    policy = RetryPolicy()
    assert policy.should_retry(_make_response(status), None) is False


@pytest.mark.parametrize(
    "exc",
    [
        httpx.ConnectError("x"),
        httpx.ConnectTimeout("x"),
        httpx.ReadTimeout("x"),
    ],
)
def test_should_retry_true_for_retryable_exceptions(exc: BaseException) -> None:
    policy = RetryPolicy()
    assert policy.should_retry(None, exc) is True


def test_should_retry_false_for_unrelated_exceptions() -> None:
    policy = RetryPolicy()
    assert policy.should_retry(None, RuntimeError("nope")) is False


def test_should_retry_false_for_no_response_no_error() -> None:
    policy = RetryPolicy()
    assert policy.should_retry(None, None) is False


# ── max_retries property ──


def test_max_retries_property_exposes_constructor_value() -> None:
    policy = RetryPolicy(max_retries=7)
    assert policy.max_retries == 7
