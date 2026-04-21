"""E2E test infrastructure.

Collected only when ``E2E_COLLECT=1`` (see ``tests/conftest.py``). Every
test in this directory is auto-marked ``e2e`` and given a 60 s timeout.
Running ``tools/tests.py --short --e2e`` sets the env var and filters to
the ``e2e`` marker.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Iterator
from contextlib import suppress
from pathlib import Path

import httpx
import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from nextlabs_sdk.cloudaz import CloudAzClient
from nextlabs_sdk.pdp import PdpClient
from tests.e2e._stubs import load_all_mappings
from tests.e2e._support import StaticBearer, register_pdp_token_stub

WIREMOCK_IMAGE = "wiremock/wiremock:3.13.0"
WIREMOCK_PORT = 8080
TEST_TOKEN = "e2e-fixture-token"
PDP_CLIENT_ID = "e2e-client"
PDP_CLIENT_SECRET = "e2e-secret"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test under ``tests/e2e/`` with ``e2e`` + ``timeout(60)``."""
    for item in items:
        if "tests/e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.timeout(60))


def _ensure_proxy_bypass() -> None:
    """Remove HTTP(S)_PROXY env vars so tests can reach the Docker bridge.

    Necessary when the environment defines an upstream corporate proxy —
    ``NO_PROXY`` doesn't understand CIDR ranges in httpx, and the
    mocked WireMock endpoint lives on an ephemeral Docker IP that can't
    be enumerated in advance.
    """
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(name, None)


def _container_ip(container: DockerContainer) -> str:
    cid = container.get_wrapped_container().id
    raw = subprocess.check_output(
        [
            "docker",
            "inspect",
            "-f",
            "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
            cid,
        ],
    )
    return raw.decode().strip()


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
    _ensure_proxy_bypass()
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
    base = f"http://{_container_ip(wiremock_container)}:{WIREMOCK_PORT}"
    httpx.post(f"{base}/__admin/mappings/reset", timeout=5.0)
    httpx.post(f"{base}/__admin/requests/reset", timeout=5.0)
    return base


@pytest.fixture
def seeded_wiremock(wiremock_base_url: str) -> str:
    """WireMock URL with spec-derived stubs and a PDP token stub loaded."""
    load_all_mappings(wiremock_base_url)
    register_pdp_token_stub(wiremock_base_url, TEST_TOKEN)
    return wiremock_base_url


@pytest.fixture
def cloudaz_client(seeded_wiremock: str) -> Iterator[CloudAzClient]:
    client = CloudAzClient(
        base_url=seeded_wiremock,
        auth=StaticBearer(TEST_TOKEN),
    )
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def pdp_client(seeded_wiremock: str) -> Iterator[PdpClient]:
    client = PdpClient(
        base_url=seeded_wiremock,
        auth_base_url=seeded_wiremock,
        client_id=PDP_CLIENT_ID,
        client_secret=PDP_CLIENT_SECRET,
    )
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def cli_runner(
    seeded_wiremock: str,
    tmp_path: Path,
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Return a callable that runs the installed ``nextlabs`` entry point."""

    def _run(
        *args: str,
        stdin: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        for proxy_var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            env.pop(proxy_var, None)
        env["NEXTLABS_BASE_URL"] = seeded_wiremock
        env["NEXTLABS_TOKEN"] = TEST_TOKEN
        env["NEXTLABS_CLIENT_SECRET"] = "e2e-client-secret"
        env["NEXTLABS_CACHE_DIR"] = str(tmp_path / "tokens.json")
        return subprocess.run(
            ["nextlabs", *args],
            capture_output=True,
            text=True,
            input=stdin,
            env=env,
            timeout=30,
            check=False,
        )

    return _run
