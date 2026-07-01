from __future__ import annotations

from nextlabs_sdk._cli._account_preferences import GlobalCachePreferences
from nextlabs_sdk._cli._account_preferences_store import AccountPreferencesStore


class AccountPrefsPlaintextAckStore:
    """Adapt the CLI preferences store to the SDK ``PlaintextAckStore`` port.

    Reads and writes the reserved global cache preference so every CLI command
    shares one remembered plaintext-storage choice. A malformed or missing
    record reads as "not acknowledged".
    """

    def __init__(self, store: AccountPreferencesStore) -> None:
        self._store = store

    def is_acknowledged(self) -> bool:
        prefs = self._store.load_global_cache()
        return prefs is not None and prefs.plaintext_acknowledged

    def remember(self) -> None:
        self._store.save_global_cache(
            GlobalCachePreferences(plaintext_acknowledged=True)
        )
