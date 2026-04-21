from __future__ import annotations

from dataclasses import dataclass

_SCHEMA_VERSION = 1


def _check_schema_version(payload: dict[str, object]) -> None:
    version = payload.get("schema_version")
    if version != _SCHEMA_VERSION:
        raise TypeError(
            f"unsupported preferences schema version: {version!r}; "
            f"expected {_SCHEMA_VERSION}",
        )


def _optional_str(payload: dict[str, object], key: str) -> str | None:
    entry = payload.get(key)
    if entry is None:
        return None
    if not isinstance(entry, str):
        raise TypeError(f"{key} must be str or None")
    return entry


@dataclass(frozen=True)
class AccountPreferences:
    """Per-account CLI preferences persisted alongside the token cache.

    Attributes:
        verify_ssl: Whether the CLI should verify TLS certificates for
            this account by default.
        pdp_url: Optional PDP base URL registered for this account via
            ``auth login --type pdp``. ``None`` for CloudAz accounts.
        pdp_auth_source: Optional PDP token-endpoint flavor registered
            for this account (``"cloudaz"`` or ``"pdp"``). ``None`` for
            CloudAz accounts.
    """

    verify_ssl: bool
    pdp_url: str | None = None
    pdp_auth_source: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "verify_ssl": self.verify_ssl,
            "pdp_url": self.pdp_url,
            "pdp_auth_source": self.pdp_auth_source,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> AccountPreferences:
        _check_schema_version(payload)
        verify_ssl = payload.get("verify_ssl")
        if not isinstance(verify_ssl, bool):
            raise TypeError("verify_ssl must be a bool")
        return cls(
            verify_ssl=verify_ssl,
            pdp_url=_optional_str(payload, "pdp_url"),
            pdp_auth_source=_optional_str(payload, "pdp_auth_source"),
        )
