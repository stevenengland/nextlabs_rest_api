import os
from collections.abc import Generator

import pytest
from mockito import unstub as mockito_unstub

# ── E2E collection guard ──
# When E2E_COLLECT is not set, ignore the e2e/ directory so pytest
# does not try to import testcontainers at collection time.
if not os.environ.get("E2E_COLLECT"):
    collect_ignore_glob = ["e2e/*"]


@pytest.fixture(autouse=True)
def _unstub() -> Generator[None, None, None]:  # pyright: ignore[reportUnusedFunction]
    """Tear down mockito stubs after every test."""
    yield
    mockito_unstub()
