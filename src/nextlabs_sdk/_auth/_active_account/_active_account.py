from __future__ import annotations

from dataclasses import dataclass
from typing import cast

_KIND_CLOUDAZ = "cloudaz"
_KIND_PDP = "pdp"
_VALID_KINDS = (_KIND_CLOUDAZ, _KIND_PDP)


@dataclass(frozen=True)
class ActiveAccount:
    """Identifiers of the cached account currently marked as active."""

    base_url: str
    username: str
    client_id: str
    kind: str = _KIND_CLOUDAZ

    def to_dict(self) -> dict[str, str]:
        return {
            "base_url": self.base_url,
            "username": self.username,
            "client_id": self.client_id,
            "kind": self.kind,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> ActiveAccount:
        base_url = payload["base_url"]
        username = payload["username"]
        client_id = payload["client_id"]
        kind = payload.get("kind", _KIND_CLOUDAZ)
        _validate_fields(base_url, username, client_id, kind)
        return cls(
            base_url=cast(str, base_url),
            username=cast(str, username),
            client_id=cast(str, client_id),
            kind=cast(str, kind),
        )


def _validate_fields(
    base_url: object,
    username: object,
    client_id: object,
    kind: object,
) -> None:
    _require_strings(base_url, username, client_id, kind)
    if kind not in _VALID_KINDS:
        raise ValueError(f"ActiveAccount.kind must be one of {_VALID_KINDS}")
    if not (base_url and client_id):
        raise ValueError("ActiveAccount base_url and client_id must be non-empty")
    if kind == _KIND_CLOUDAZ and not username:
        raise ValueError("ActiveAccount.username must be non-empty for kind=cloudaz")


def _require_strings(*fields: object) -> None:
    for field in fields:
        if not isinstance(field, str):
            raise ValueError("ActiveAccount fields must be strings")
