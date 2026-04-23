"""Flexible time-range input parser for CLI commands.

Accepts three input shapes and returns an epoch-millisecond integer:

- Epoch milliseconds, e.g. ``1737014400000``.
- Relative offsets, e.g. ``5m`` meaning "5 minutes before now". Supported
  units are ``s``, ``m``, ``h``, ``d``, ``w``.
- ISO 8601 datetimes parsed by :func:`datetime.fromisoformat`. Naive
  values are interpreted as UTC.

Exposes :func:`parse_time` as the sole public entry point. The function
raises :class:`ValueError` with a user-facing message listing accepted
formats for any input that does not match one of the three shapes.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from types import MappingProxyType

_ACCEPTED_FORMATS_MSG = (
    "accepted formats: epoch milliseconds (e.g. 1737014400000), "
    "ISO 8601 datetime (e.g. 2024-01-15T10:30:00 or 2024-01-15T10:30:00+02:00), "
    "or relative offset (e.g. 30s, 5m, 2h, 3d, 1w)"
)

_EPOCH_MS_RE = re.compile(r"\A\d+\Z")
_RELATIVE_RE = re.compile(r"\A(\d+)([smhdw])\Z")

_UNIT_TO_MS: MappingProxyType[str, int] = MappingProxyType(
    {
        "s": 1_000,
        "m": 60 * 1_000,
        "h": 60 * 60 * 1_000,
        "d": 24 * 60 * 60 * 1_000,
        "w": 7 * 24 * 60 * 60 * 1_000,
    },
)


def now_epoch_ms() -> int:
    """Return the current wall-clock time as epoch milliseconds."""
    return int(time.time() * 1000)


def parse_time(text: str, now_ms: int | None = None) -> int:
    """Parse a CLI date string to epoch milliseconds.

    Args:
        text: Date string in one of the accepted formats.
        now_ms: Reference "now" in epoch ms used to resolve relative
            offsets. Defaults to the wall clock when ``None``.

    Returns:
        The resolved instant as epoch milliseconds.

    Raises:
        ValueError: If ``text`` does not match any accepted format.
    """
    if _EPOCH_MS_RE.match(text):
        return int(text)

    relative = _RELATIVE_RE.match(text)
    if relative is not None:
        amount = int(relative.group(1))
        unit_ms = _UNIT_TO_MS[relative.group(2)]
        reference = now_epoch_ms() if now_ms is None else now_ms
        return reference - amount * unit_ms

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            f"invalid date value {text!r}; {_ACCEPTED_FORMATS_MSG}",
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)
