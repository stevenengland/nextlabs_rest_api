from __future__ import annotations

from enum import Enum


class RefreshDecision(Enum):
    """Outcome of evaluating whether a cached refresh token is usable.

    Attributes:
        ABSENT: No refresh token is available.
        USE_REFRESH: A refresh token is present and either its expiry is
            unknown-but-reactive, or its expiry is configured and still
            in the future.
        KNOWN_EXPIRED: The refresh token's configured lifetime has
            elapsed; calling the token endpoint with it would fail.
        UNKNOWN_EXPIRY: Reserved for callers that want to distinguish
            "lifetime not configured" from "configured and still valid".
            ``decide`` folds this case into ``USE_REFRESH`` for the
            caller's convenience; tests may still assert on it via
            :func:`classify`.
    """

    ABSENT = "absent"
    USE_REFRESH = "use_refresh"
    KNOWN_EXPIRED = "known_expired"
    UNKNOWN_EXPIRY = "unknown_expiry"


def decide(
    *,
    refresh_token: str | None,
    refresh_expires_at: float | None,
    now: float,
) -> RefreshDecision:
    """Decide how to treat a cached refresh token.

    Pure function; no I/O, no global clock. Inputs:

    - ``refresh_token``: the cached refresh token (or ``None``).
    - ``refresh_expires_at``: absolute epoch seconds at which the
      refresh token is considered expired, or ``None`` when the SDK
      has no information (reactive mode — lifetime unconfigured or
      cache entry predates the configuration).
    - ``now``: current absolute epoch seconds.

    Returns:
        :class:`RefreshDecision`:

        * ``ABSENT`` when ``refresh_token`` is ``None``.
        * ``KNOWN_EXPIRED`` when an expiry is known and ``now >=`` it.
        * ``USE_REFRESH`` otherwise — including the reactive case where
          expiry is unknown.
    """
    if refresh_token is None:
        return RefreshDecision.ABSENT
    if refresh_expires_at is not None and now >= refresh_expires_at:
        return RefreshDecision.KNOWN_EXPIRED
    return RefreshDecision.USE_REFRESH
