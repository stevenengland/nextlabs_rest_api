from __future__ import annotations

import time
from datetime import datetime, timezone

_SECONDS_PER_MINUTE = 60
_SECONDS_PER_HOUR = 60 * _SECONDS_PER_MINUTE
_SECONDS_PER_DAY = 24 * _SECONDS_PER_HOUR


def _relative_phrase(delta_seconds: float) -> str:
    delta = int(abs(delta_seconds))
    if delta >= _SECONDS_PER_DAY:
        amount, unit = delta // _SECONDS_PER_DAY, "day"
    elif delta >= _SECONDS_PER_HOUR:
        amount, unit = delta // _SECONDS_PER_HOUR, "hour"
    elif delta >= _SECONDS_PER_MINUTE:
        amount, unit = delta // _SECONDS_PER_MINUTE, "minute"
    else:
        amount, unit = delta, "second"
    plural = "" if amount == 1 else "s"
    return f"{amount} {unit}{plural}"


def format_expiry(epoch_seconds: float, *, now: float | None = None) -> str:
    """Render an epoch timestamp as ISO-8601 UTC plus a relative phrase.

    Args:
        epoch_seconds: Absolute expiration in seconds since the UNIX epoch.
        now: Optional override for the current time (used by tests).

    Returns:
        A string like ``"2026-04-17T18:45:44Z (in 59 minutes)"`` for a future
        timestamp or ``"2026-04-17T18:45:44Z (expired 3 minutes ago)"`` for a
        past one. The relative phrase uses the largest non-zero unit among
        days, hours, minutes, and seconds. If ``epoch_seconds`` is outside the
        range representable by :class:`datetime.datetime`, the absolute
        portion falls back to ``"epoch=<value>"``.
    """
    reference = time.time() if now is None else now
    delta = epoch_seconds - reference
    try:
        absolute = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ",
        )
    except (OverflowError, ValueError, OSError):
        absolute = f"epoch={epoch_seconds}"
    phrase = _relative_phrase(delta)
    qualifier = f"in {phrase}" if delta >= 0 else f"expired {phrase} ago"
    return f"{absolute} ({qualifier})"
