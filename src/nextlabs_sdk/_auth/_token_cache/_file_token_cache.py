from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._token_cache import TokenCache

_FILE_MODE = 0o600
_DIR_MODE = 0o700
_CACHE_FILENAME = "tokens.json"
_PACKAGE_DIR = "nextlabs-sdk"


def _default_path() -> Path:
    override = os.environ.get("NEXTLABS_CACHE_DIR")
    if override:
        return Path(override) / _CACHE_FILENAME

    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / _PACKAGE_DIR / _CACHE_FILENAME

    return Path.home() / ".cache" / _PACKAGE_DIR / _CACHE_FILENAME


class FileTokenCache(TokenCache):
    """JSON-backed token cache with atomic writes and ``0600`` permissions."""

    def __init__(self, *, path: Path | str | None = None) -> None:
        self._path = _default_path() if path is None else Path(path)

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

    def _read_all(self) -> dict[str, object]:
        if not self._path.exists():
            return {}
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                loaded = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(loaded, dict):
            return {}
        return loaded

    def _write_all(self, entries: dict[str, object]) -> None:
        directory = self._path.parent
        directory.mkdir(parents=True, exist_ok=True)
        os.chmod(directory, _DIR_MODE)

        fd, tmp_name = tempfile.mkstemp(
            prefix=".tokens-",
            suffix=".tmp",
            dir=str(directory),
        )
        try:
            self._atomic_write(fd, tmp_name, entries)
        except Exception:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise

    def _atomic_write(
        self,
        fd: int,
        tmp_name: str,
        entries: dict[str, object],
    ) -> None:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(entries, fh)
        os.chmod(tmp_name, _FILE_MODE)
        os.replace(tmp_name, self._path)
