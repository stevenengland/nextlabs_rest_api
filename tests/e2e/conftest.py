"""E2E test infrastructure.

This conftest provides fixtures for end-to-end tests using testcontainers.
Tests in this directory are only collected when E2E_COLLECT=1 is set
(see tests/conftest.py for the collection guard).

Usage:
    python ./tools/tests.py --short --e2e
"""

import pytest

# ── Example: WireMock container fixture ──
# from testcontainers.core.container import DockerContainer
#
# @pytest.fixture(scope="session")
# def wiremock_container():
#     container = DockerContainer("wiremock/wiremock:3.13.0")
#     container.with_exposed_ports(8080)
#     container.start()
#     yield container
#     container.stop()


@pytest.mark.e2e
def test_example_e2e() -> None:
    """Example E2E test — replace with real container-backed tests."""
    assert True
