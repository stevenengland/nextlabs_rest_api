from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from nextlabs_sdk._auth._active_account._active_account import ActiveAccount

_FILE_MODE = 0o600
_DIR_MODE = 0o700
_FILENAME = "active_account.json"
_PACKAGE_DIR = "nextlabs-sdk"


def _default_path() -> Path:
    override = os.environ.get("NEXTLABS_CACHE_DIR")
    if override:
        return Path(override) / _FILENAME

    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / _PACKAGE_DIR / _FILENAME

    return Path.home() / ".cache" / _PACKAGE_DIR / _FILENAME


class ActiveAccountStore:
    """JSON-backed pointer to the currently active cached account."""

    def __init__(self, *, path: Path | str | None = None) -> None:
        self._path = _default_path() if path is None else Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> ActiveAccount | None:
        if not self._path.exists():
            return None
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                loaded = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(loaded, dict):
            return None
        try:
            return ActiveAccount.from_dict(loaded)
        except (KeyError, TypeError, ValueError):
            return None

    def save(self, account: ActiveAccount) -> None:
        directory = self._path.parent
        directory.mkdir(parents=True, exist_ok=True)
        os.chmod(directory, _DIR_MODE)

        fd, tmp_name = tempfile.mkstemp(
            prefix=".active-",
            suffix=".tmp",
            dir=str(directory),
        )
        try:
            self._atomic_write(fd, tmp_name, account)
        except Exception:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise

    def clear(self) -> None:
        try:
            self._path.unlink()
        except FileNotFoundError:
            return

    def _atomic_write(
        self,
        fd: int,
        tmp_name: str,
        account: ActiveAccount,
    ) -> None:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(account.to_dict(), fh)
        os.chmod(tmp_name, _FILE_MODE)
        os.replace(tmp_name, self._path)
