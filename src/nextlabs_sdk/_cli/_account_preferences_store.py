from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from nextlabs_sdk._cli._account_preferences import AccountPreferences

_FILE_MODE = 0o600
_DIR_MODE = 0o700
_FILENAME = "account_prefs.json"
_PACKAGE_DIR = "nextlabs-sdk"


def _default_path() -> Path:
    override = os.environ.get("NEXTLABS_CACHE_DIR")
    if override:
        return Path(override) / _FILENAME

    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / _PACKAGE_DIR / _FILENAME

    return Path.home() / ".cache" / _PACKAGE_DIR / _FILENAME


class AccountPreferencesStore:
    """JSON-backed per-account preference store.

    Mirrors the token cache layout (``NEXTLABS_CACHE_DIR`` →
    ``XDG_CACHE_HOME`` → ``~/.cache``) but lives in a separate file so
    future keyring-backed token storage does not disturb it. Writes are
    atomic with ``0600`` permissions in a ``0700`` directory. Malformed
    or missing payloads are treated as "no preference set" rather than
    raising.
    """

    def __init__(self, *, path: Path | str | None = None) -> None:
        self._path = _default_path() if path is None else Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def load(self, key: str) -> AccountPreferences | None:
        entries = self._read_all()
        entry = entries.get(key)
        if not isinstance(entry, dict):
            return None
        try:
            return AccountPreferences.from_dict(entry)
        except (KeyError, TypeError, ValueError):
            return None

    def save(self, key: str, prefs: AccountPreferences) -> None:
        entries = self._read_all()
        entries[key] = prefs.to_dict()
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
            prefix=".prefs-",
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
