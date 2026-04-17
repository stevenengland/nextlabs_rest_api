from __future__ import annotations

import time
from dataclasses import dataclass

_DEFAULT_SAFETY_MARGIN = 60
_SCHEMA_VERSION = 2


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


def _check_schema_version(payload: dict[str, object]) -> None:
    version = payload.get("schema_version")
    if version != _SCHEMA_VERSION:
        raise TypeError(
            f"unsupported cache schema version: {version!r}; "
            f"expected {_SCHEMA_VERSION}",
        )


def _coerce_refresh_expires_at(raw: object) -> float | None:
    if raw is None:
        return None
    if not isinstance(raw, (int, float)):
        raise TypeError("refresh_expires_at must be a number or None")
    return float(raw)


@dataclass(frozen=True)
class CachedToken:
    """A persisted OIDC token.

    Attributes:
        access_token: The OAuth2 access_token used as the bearer credential.
        refresh_token: Optional refresh_token for silent re-auth.
        expires_at: Absolute UTC epoch seconds at which the token expires.
        token_type: OAuth token type (typically ``"bearer"``).
        scope: Optional OAuth scope string.
        refresh_expires_at: Absolute UTC epoch seconds at which the
            refresh token is considered expired, or ``None`` when the
            SDK has no information (reactive mode).
    """

    access_token: str
    refresh_token: str | None
    expires_at: float
    token_type: str
    scope: str | None
    refresh_expires_at: float | None = None

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
            "schema_version": _SCHEMA_VERSION,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "token_type": self.token_type,
            "scope": self.scope,
            "refresh_expires_at": self.refresh_expires_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> CachedToken:
        """Deserialize from a mapping produced by :meth:`to_dict`.

        Entries written by older schema versions (missing or mismatched
        ``schema_version``) are rejected by raising :class:`TypeError`,
        which cache backends treat as "entry absent" so users re-login
        once after an SDK upgrade.
        """
        _check_schema_version(payload)
        access_token = _require(payload, "access_token", str)
        refresh_token = _optional(payload, "refresh_token", str)
        expires_at_raw = payload.get("expires_at")
        if not isinstance(expires_at_raw, (int, float)):
            raise TypeError("expires_at must be a number")
        token_type = _require(payload, "token_type", str)
        scope = _optional(payload, "scope", str)
        refresh_expires_at_raw = payload.get("refresh_expires_at")
        refresh_expires_at = _coerce_refresh_expires_at(refresh_expires_at_raw)

        assert isinstance(access_token, str)
        assert refresh_token is None or isinstance(refresh_token, str)
        assert isinstance(token_type, str)
        assert scope is None or isinstance(scope, str)

        return cls(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=float(expires_at_raw),
            token_type=token_type,
            scope=scope,
            refresh_expires_at=refresh_expires_at,
        )
