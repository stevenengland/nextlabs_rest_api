from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nextlabs_sdk._cloudaz._search.payloads import date_payload
from nextlabs_sdk.exceptions import SearchExpressionError

_RANGE_SEP = ".."
_MILLIS_PER_SECOND = 1000

DATE_KEYWORDS = frozenset(
    (
        "PAST_7_DAYS",
        "PAST_30_DAYS",
        "PAST_3_MONTHS",
        "PAST_1_YEAR",
    ),
)


def date_value(raw: str) -> dict[str, Any]:
    """Parse a DATE value into a CloudAz date payload.

    A keyword (``PAST_7_DAYS``, ``PAST_30_DAYS``, ``PAST_3_MONTHS``,
    ``PAST_1_YEAR``) yields a ``dateOption`` payload. A ``from..to`` range of
    ISO dates yields ``fromDate``/``toDate`` bounds in UTC epoch-milliseconds.

    Args:
        raw: The raw DATE value, either a keyword or a ``from..to`` range.

    Returns:
        The date payload dict, tagged with a ``Date`` type label.

    Raises:
        SearchExpressionError: If the value is neither a known keyword nor a
            valid ISO range.
    """
    token = raw.strip()
    if _RANGE_SEP in token:
        return _range_payload(token)
    keyword = token.upper()
    if keyword in DATE_KEYWORDS:
        return date_payload(dateOption=keyword)
    raise SearchExpressionError(
        f"date value must be a keyword or from..to range: {raw!r}",
    )


def _range_payload(token: str) -> dict[str, Any]:
    from_part, _, to_part = token.partition(_RANGE_SEP)
    return date_payload(
        fromDate=epoch_millis(from_part),
        toDate=epoch_millis(to_part),
    )


def epoch_millis(bound: str) -> int:
    """Parse an ISO date bound into UTC epoch-milliseconds.

    A naive date is interpreted as UTC; an explicit offset is honoured.

    Args:
        bound: The raw ISO date bound.

    Returns:
        The bound as integer milliseconds since the Unix epoch.

    Raises:
        SearchExpressionError: If the bound is empty or not a valid ISO date.
    """
    text = bound.strip()
    if not text:
        raise SearchExpressionError("date range bound is missing")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise SearchExpressionError(
            f"date range bound is not a valid ISO date: {bound!r}",
        ) from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * _MILLIS_PER_SECOND)
