from __future__ import annotations

import json
from pathlib import Path

from nextlabs_sdk._auth._token_cache._atomic_write import atomic_write_bytes
from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._secret_box import (
    PassphraseKek,
    RawKek,
    SecretBox,
)
from nextlabs_sdk._auth._token_cache._token_cache import TokenCache

_FILE_MODE = 0o600
_DIR_MODE = 0o700


class EncryptedFileTokenCache(TokenCache):
    """Token cache that reads plaintext or ``NLBX`` and always writes encrypted.

    Reading a legacy plaintext file leaves it untouched; the next ``save``
    rewrites it as an ``NLBX`` envelope. The unwrapped data-encryption key is
    cached in-process so the Argon2 key derivation runs at most once per
    process across all loads and saves.
    """

    def __init__(self, *, path: Path | str, kek_source: PassphraseKek | RawKek) -> None:
        self._path = Path(path)
        self._kek_source = kek_source
        self._box: SecretBox | None = None

    @property
    def path(self) -> Path:
        return self._path

    def load(self, key: str) -> CachedToken | None:
        entries = self._read_all()
        entry = entries.get(key)
        if not isinstance(entry, dict):
            return None
        try:
            return CachedToken.from_dict(entry)
        except (KeyError, TypeError, ValueError):
            return None

    def save(self, key: str, token: CachedToken) -> None:
        entries = self._read_all()
        entries[key] = token.to_dict()
        self._write_all(entries)

    def delete(self, key: str) -> None:
        entries = self._read_all()
        if entries.pop(key, None) is not None:
            self._write_all(entries)

    def keys(self) -> list[str]:
        return list(self._read_all().keys())

    def _read_all(self) -> dict[str, object]:
        if not self._path.exists():
            return {}
        blob = self._path.read_bytes()
        if not blob:
            return {}
        if SecretBox.is_encrypted(blob):
            if self._box is None:
                self._box = SecretBox.unlock(blob, self._kek_source)
            loaded = json.loads(self._box.decrypt(blob))
            return loaded if isinstance(loaded, dict) else {}
        try:
            loaded = json.loads(blob.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return loaded if isinstance(loaded, dict) else {}

    def _write_all(self, entries: dict[str, object]) -> None:
        if self._box is None:
            self._box = SecretBox.seal_new(self._kek_source)
        blob = self._box.encrypt(json.dumps(entries).encode("utf-8"))
        atomic_write_bytes(
            self._path,
            blob,
            dir_mode=_DIR_MODE,
            file_mode=_FILE_MODE,
        )
