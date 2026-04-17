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


@dataclass(frozen=True)
class AccountPreferences:
    """Per-account CLI preferences persisted alongside the token cache.

    Attributes:
        verify_ssl: Whether the CLI should verify TLS certificates for
            this account by default.
    """

    verify_ssl: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "verify_ssl": self.verify_ssl,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> AccountPreferences:
        _check_schema_version(payload)
        verify_ssl = payload.get("verify_ssl")
        if not isinstance(verify_ssl, bool):
            raise TypeError("verify_ssl must be a bool")
        return cls(verify_ssl=verify_ssl)
