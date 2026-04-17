from __future__ import annotations

import time
from dataclasses import dataclass

_DEFAULT_SAFETY_MARGIN = 60


def _require(payload: dict[str, object], key: str, expected: type) -> object:
    entry = payload.get(key)
    if not isinstance(entry, expected):
        raise TypeError(f"{key} must be {expected.__name__}")
    return entry


def _optional(payload: dict[str, object], key: str, expected: type) -> object:
    entry = payload.get(key)
    if entry is not None and not isinstance(entry, expected):
        raise TypeError(f"{key} must be {expected.__name__} or None")
    return entry


@dataclass(frozen=True)
class CachedToken:
    """A persisted OIDC token.

    Attributes:
        id_token: The OIDC id_token used as the bearer credential.
        refresh_token: Optional refresh_token for silent re-auth.
        expires_at: Absolute UTC epoch seconds at which the token expires.
        token_type: OAuth token type (typically ``"bearer"``).
        scope: Optional OAuth scope string.
    """

    id_token: str
    refresh_token: str | None
    expires_at: float
    token_type: str
    scope: str | None

    def is_expired(
        self,
        *,
        now: float | None = None,
        safety_margin: float = _DEFAULT_SAFETY_MARGIN,
    ) -> bool:
        """Return True when the token is at or past its expiry."""
        effective_now = time.time() if now is None else now
        return effective_now + safety_margin >= self.expires_at

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible mapping."""
        return {
            "id_token": self.id_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "token_type": self.token_type,
            "scope": self.scope,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> CachedToken:
        """Deserialize from a mapping produced by :meth:`to_dict`."""
        id_token = _require(payload, "id_token", str)
        refresh_token = _optional(payload, "refresh_token", str)
        expires_at_raw = payload.get("expires_at")
        if not isinstance(expires_at_raw, (int, float)):
            raise TypeError("expires_at must be a number")
        token_type = _require(payload, "token_type", str)
        scope = _optional(payload, "scope", str)

        assert isinstance(id_token, str)
        assert refresh_token is None or isinstance(refresh_token, str)
        assert isinstance(token_type, str)
        assert scope is None or isinstance(scope, str)

        return cls(
            id_token=id_token,
            refresh_token=refresh_token,
            expires_at=float(expires_at_raw),
            token_type=token_type,
            scope=scope,
        )
