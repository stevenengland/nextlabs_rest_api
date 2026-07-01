from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PlaintextAckStore(Protocol):
    """Port for persisting the user's plaintext-storage acknowledgement.

    The token-cache factory consults this port only when no passphrase source
    resolves. An acknowledged choice lets the factory return a plaintext cache
    without prompting; :meth:`remember` records that choice so later builds stay
    silent. Implementations live outside the SDK core (for example, the CLI
    preferences store) and are injected into ``build_token_cache``.
    """

    def is_acknowledged(self) -> bool:
        """Return whether plaintext storage has been remembered."""
        ...

    def remember(self) -> None:
        """Persist the plaintext-storage acknowledgement."""
        ...
