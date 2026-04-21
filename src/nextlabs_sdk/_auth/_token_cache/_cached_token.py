from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TypeAlias, cast

_DEFAULT_SAFETY_MARGIN = 60
_SCHEMA_VERSION = 3

_OptStr: TypeAlias = "str | None"


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
        access_token: The OAuth2 access_token returned by the token
            endpoint. Retained for diagnostics and refresh flows;
            CloudAz requests now authenticate with ``id_token``.
        refresh_token: Optional refresh_token for silent re-auth.
        expires_at: Absolute UTC epoch seconds at which the token expires.
        token_type: OAuth token type (typically ``"bearer"``).
        scope: Optional OAuth scope string.
        id_token: OIDC ``id_token`` sent as the bearer credential on
            CloudAz API requests. ``None`` on cache entries written by
            older SDK versions; callers should treat such entries as
            expired and trigger a refresh.
        refresh_expires_at: Absolute UTC epoch seconds at which the
            refresh token is considered expired, or ``None`` when the
            SDK has no information (reactive mode).
        client_secret: Optional OAuth2 client_secret persisted alongside
            the token so PDP accounts can mint a fresh token silently
            without re-prompting. Stored plain in ``tokens.json``
            (mode 0600), mirroring ``refresh_token``.
    """

    access_token: str
    refresh_token: str | None
    expires_at: float
    token_type: str
    scope: str | None
    id_token: str | None = None
    refresh_expires_at: float | None = None
    client_secret: str | None = None

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
            "id_token": self.id_token,
            "refresh_expires_at": self.refresh_expires_at,
            "client_secret": self.client_secret,
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
        id_token = _optional(payload, "id_token", str)
        refresh_expires_at_raw = payload.get("refresh_expires_at")
        refresh_expires_at = _coerce_refresh_expires_at(refresh_expires_at_raw)
        client_secret = _optional(payload, "client_secret", str)

        return cls(
            access_token=cast(str, access_token),
            refresh_token=cast(_OptStr, refresh_token),
            expires_at=float(expires_at_raw),
            token_type=cast(str, token_type),
            scope=cast(_OptStr, scope),
            id_token=cast(_OptStr, id_token),
            refresh_expires_at=refresh_expires_at,
            client_secret=cast(_OptStr, client_secret),
        )
