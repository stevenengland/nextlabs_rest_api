"""Labels for cached-token status in the ``auth status`` output."""

from __future__ import annotations

import time

from nextlabs_sdk._auth._refresh_token_policy import RefreshDecision, decide
from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._cli._expiry_format import format_expiry

_STATUS_NONE = "—"


def account_status_and_refreshable(entry: CachedToken | None) -> tuple[str, str]:
    return _status_label(entry), _refreshable_label(entry)


def _status_label(entry: CachedToken | None) -> str:
    if entry is None:
        return "no cached token"
    qualifier = "expired" if entry.is_expired() else "valid"
    parts = [f"{qualifier} (expires {format_expiry(entry.expires_at)}"]
    if entry.refresh_expires_at is not None:
        parts.append(f"; refresh expires {format_expiry(entry.refresh_expires_at)}")
    parts.append(")")
    return "".join(parts)


def _refreshable_label(entry: CachedToken | None) -> str:
    if entry is None:
        return _STATUS_NONE
    return _refresh_decision_label(entry)


def _refresh_decision_label(entry: CachedToken) -> str:
    decision = decide(
        refresh_token=entry.refresh_token,
        refresh_expires_at=entry.refresh_expires_at,
        now=time.time(),
    )
    if decision is RefreshDecision.USE_REFRESH:
        return "yes"
    if decision is RefreshDecision.KNOWN_EXPIRED:
        return "no (expired)"
    return "no"
