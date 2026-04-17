from __future__ import annotations

from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._token_cache import TokenCache


class NullTokenCache(TokenCache):
    """No-op cache. Default for SDK library consumers."""

    def load(self, key: str) -> CachedToken | None:
        """Always return None."""

    def save(self, key: str, token: CachedToken) -> None:
        """No-op."""

    def delete(self, key: str) -> None:
        """No-op."""

    def keys(self) -> list[str]:
        """Always return an empty list."""
        return []
