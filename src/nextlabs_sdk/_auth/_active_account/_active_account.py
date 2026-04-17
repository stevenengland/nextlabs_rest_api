from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActiveAccount:
    """Identifiers of the cached account currently marked as active."""

    base_url: str
    username: str
    client_id: str

    def to_dict(self) -> dict[str, str]:
        return {
            "base_url": self.base_url,
            "username": self.username,
            "client_id": self.client_id,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> ActiveAccount:
        base_url = payload["base_url"]
        username = payload["username"]
        client_id = payload["client_id"]
        if not (
            isinstance(base_url, str)
            and isinstance(username, str)
            and isinstance(client_id, str)
        ):
            raise ValueError("ActiveAccount fields must be strings")
        if not (base_url and username and client_id):
            raise ValueError("ActiveAccount fields must be non-empty")
        return cls(base_url=base_url, username=username, client_id=client_id)
