from __future__ import annotations

from typing import Protocol

_TOKEN_PATH_SUFFIX = "/cas/oidc/accessToken"


class _AccountKeyFields(Protocol):
    @property
    def base_url(self) -> str: ...
    @property
    def username(self) -> str: ...
    @property
    def client_id(self) -> str: ...


def cache_key_for(account: _AccountKeyFields) -> str:
    """Build the token-cache key for an account.

    Single source of truth for the cache-key format. Accepts any object
    exposing ``base_url``, ``username``, and ``client_id`` (e.g.
    ``AccountIdentifier`` from ``_account_menu`` or ``ResolvedAccount``
    from ``_account_resolver``) so callers don't have to convert between
    structurally-equivalent dataclasses.
    """
    return (
        f"{account.base_url}{_TOKEN_PATH_SUFFIX}"
        f"|{account.username}|{account.client_id}"
    )


def parse_cache_key(key: str) -> tuple[str, str, str] | None:
    """Parse a token-cache key into ``(base_url, username, client_id)``.

    Returns ``None`` when the key does not match the expected format.
    """
    parts = key.split("|")
    if len(parts) != 3:
        return None
    base_part, username, client_id = parts
    if not base_part.endswith(_TOKEN_PATH_SUFFIX):
        return None
    base_url = base_part[: -len(_TOKEN_PATH_SUFFIX)]
    if not (base_url and username and client_id):
        return None
    return base_url, username, client_id
