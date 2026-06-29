import os
from collections.abc import Generator
from pathlib import Path

import pytest
from keyring.errors import NoKeyringError
from mockito import unstub as mockito_unstub

# ── E2E collection guard ──
# When E2E_COLLECT is not set, ignore the e2e/ directory so pytest
# does not try to import testcontainers at collection time.
if not os.environ.get("E2E_COLLECT"):
    collect_ignore_glob = ["e2e/*"]


@pytest.fixture(autouse=True)
def _isolate_nextlabs_cache(  # pyright: ignore[reportUnusedFunction]
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Point cache lookups at a per-test temp dir.

    Without this, tests that exercise ``resolve_account`` or the file
    token cache silently read the developer's real
    ``~/.cache/nextlabs-sdk/`` directory and pick up stale login state,
    causing non-reproducible failures across machines. Individual tests
    that need a specific override can still call ``monkeypatch.setenv``
    or ``monkeypatch.delenv`` — those take effect after this fixture.
    """
    cache_dir: Path = tmp_path_factory.mktemp("nextlabs-cache")
    monkeypatch.setenv("NEXTLABS_CACHE_DIR", str(cache_dir))
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)


@pytest.fixture(autouse=True)
def _disable_real_keyring(  # pyright: ignore[reportUnusedFunction]
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Force the keyring to behave as if no backend is installed.

    Otherwise the keyring passphrase source would auto-generate and persist a
    key into the developer's (or CI runner's) OS keychain on platforms where a
    backend is installed, encrypting the token cache and making outcomes depend
    on the host. Tests that exercise the keyring path stub these ``keyring``
    module functions directly, overriding this default.
    """

    def _no_backend(*_args: object, **_kwargs: object) -> None:
        raise NoKeyringError()

    monkeypatch.setattr("keyring.get_password", _no_backend)
    monkeypatch.setattr("keyring.set_password", _no_backend)
    monkeypatch.setattr("keyring.delete_password", _no_backend)


@pytest.fixture(autouse=True)
def _unstub() -> Generator[None, None, None]:  # pyright: ignore[reportUnusedFunction]
    """Tear down mockito stubs after every test."""
    yield
    mockito_unstub()
