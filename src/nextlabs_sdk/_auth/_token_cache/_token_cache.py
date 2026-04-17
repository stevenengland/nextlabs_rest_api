from __future__ import annotations

from abc import ABC, abstractmethod

from nextlabs_sdk._auth._token_cache._cached_token import CachedToken


class TokenCache(ABC):
    """Pluggable persistence backend for OIDC tokens."""

    @abstractmethod
    def load(self, key: str) -> CachedToken | None:
        """Return the cached token for ``key``, or ``None`` if absent/corrupt."""

    @abstractmethod
    def save(self, key: str, token: CachedToken) -> None:
        """Persist ``token`` under ``key``, atomically when possible."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove the entry under ``key``. No-op if the entry does not exist."""
