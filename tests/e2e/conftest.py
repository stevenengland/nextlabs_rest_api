"""E2E test infrastructure.

Collected only when ``E2E_COLLECT=1`` (see ``tests/conftest.py``). Every
test in this directory is auto-marked ``e2e`` and given a 60 s timeout.
Running ``tools/tests.py --short --e2e`` sets the env var and filters to
the ``e2e`` marker.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import suppress

import httpx
import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

WIREMOCK_IMAGE = "wiremock/wiremock:3.13.0"
WIREMOCK_PORT = 8080


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test under ``tests/e2e/`` with ``e2e`` + ``timeout(60)``."""
    for item in items:
        if "tests/e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.timeout(60))


def _ensure_docker_reachable() -> None:
    try:
        container = DockerContainer("hello-world")
        container.start()
    except (OSError, RuntimeError) as exc:
        pytest.skip(f"Docker not available; skipping E2E tests ({exc})")
    with suppress(OSError, RuntimeError):
        container.stop()


@pytest.fixture(scope="session")
def wiremock_container() -> Iterator[DockerContainer]:
    """Start a single WireMock container for the whole test session."""
    _ensure_docker_reachable()
    container = DockerContainer(WIREMOCK_IMAGE).with_exposed_ports(
        WIREMOCK_PORT,
    )
    container.start()
    wait_for_logs(container, "verbose:", timeout=30)
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture
def wiremock_base_url(wiremock_container: DockerContainer) -> str:
    """HTTP base URL for WireMock, freshly reset for each test."""
    host = wiremock_container.get_container_host_ip()
    port = wiremock_container.get_exposed_port(WIREMOCK_PORT)
    base = f"http://{host}:{port}"
    httpx.post(f"{base}/__admin/mappings/reset", timeout=5.0)
    httpx.post(f"{base}/__admin/requests/reset", timeout=5.0)
    return base
