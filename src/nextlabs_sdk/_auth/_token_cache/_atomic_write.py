from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write_bytes(
    path: Path,
    payload: bytes,
    *,
    dir_mode: int = 0o700,
    file_mode: int = 0o600,
) -> None:
    """Write ``payload`` to ``path`` atomically with restrictive permissions."""
    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, dir_mode)

    fd, tmp_name = tempfile.mkstemp(
        prefix=".tokens-", suffix=".tmp", dir=str(directory)
    )
    try:
        _commit(fd, tmp_name, payload, path, file_mode)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def _commit(
    fd: int,
    tmp_name: str,
    payload: bytes,
    path: Path,
    file_mode: int,
) -> None:
    with os.fdopen(fd, "wb") as fh:
        fh.write(payload)
    os.chmod(tmp_name, file_mode)
    os.replace(tmp_name, path)
