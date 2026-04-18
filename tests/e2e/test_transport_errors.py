"""Transport-level error paths, exercised once (not per service).

Exercises the shared transport layer directly so that we cover the
``_STATUS_CODE_MAP`` to :class:`NextLabsError` subclass mapping without
coupling the assertions to any one endpoint's contract. We deliberately
reach for the underlying :class:`httpx.Client` via the SDK's private
``_client`` attribute — acceptable inside E2E tests whose intent is to
probe the transport itself.
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest

from nextlabs_sdk import HttpConfig, RetryConfig
from nextlabs_sdk.cloudaz import CloudAzClient
from nextlabs_sdk.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NextLabsError,
    NotFoundError,
    RateLimitError,
    RequestTimeoutError,
    ServerError,
    raise_for_status,
)
from tests.e2e._support import StaticBearer

from types import MappingProxyType

TEST_TOKEN = "e2e-fixture-token"
_STATUS_PATH: MappingProxyType[int, str] = MappingProxyType(
    {
        401: "/e2e/errors/unauthorized",
        403: "/e2e/errors/forbidden",
        404: "/e2e/errors/not-found",
        409: "/e2e/errors/conflict",
        429: "/e2e/errors/rate-limited",
        500: "/e2e/errors/server",
    },
)
_TIMEOUT_PATH = "/e2e/errors/slow"


@pytest.fixture
def error_stubs(seeded_wiremock: str) -> str:
    with httpx.Client(timeout=5.0) as http:
        for status, path in _STATUS_PATH.items():
            http.post(
                f"{seeded_wiremock}/__admin/mappings",
                json={
                    "priority": 1,
                    "request": {"method": "GET", "urlPath": path},
                    "response": {"status": status, "body": ""},
                },
            )
        http.post(
            f"{seeded_wiremock}/__admin/mappings",
            json={
                "priority": 1,
                "request": {"method": "GET", "urlPath": _TIMEOUT_PATH},
                "response": {
                    "status": 200,
                    "body": "ok",
                    "fixedDelayMilliseconds": 2000,
                },
            },
        )
    return seeded_wiremock


@pytest.fixture
def no_retry_client(error_stubs: str) -> Iterator[CloudAzClient]:
    """CloudAz client with retries disabled so 429/500 fail fast."""
    client = CloudAzClient(
        base_url=error_stubs,
        auth=StaticBearer(TEST_TOKEN),
        http_config=HttpConfig(retry=RetryConfig(max_retries=0)),
    )
    try:
        yield client
    finally:
        client.close()


@pytest.mark.parametrize(
    ("status", "exc"),
    [
        (401, AuthenticationError),
        (403, AuthorizationError),
        (404, NotFoundError),
        (409, ConflictError),
        (429, RateLimitError),
        (500, ServerError),
    ],
)
def test_status_maps_to_exception(
    no_retry_client: CloudAzClient,
    status: int,
    exc: type[NextLabsError],
) -> None:
    response = no_retry_client._client.get(_STATUS_PATH[status])
    with pytest.raises(exc):
        raise_for_status(response)


def test_timeout_raises_nextlabs_error(error_stubs: str) -> None:
    client = CloudAzClient(
        base_url=error_stubs,
        auth=StaticBearer(TEST_TOKEN),
        http_config=HttpConfig(
            timeout=0.5,
            retry=RetryConfig(max_retries=0),
        ),
    )
    try:
        with pytest.raises(
            (RequestTimeoutError, NextLabsError, httpx.TimeoutException)
        ):
            client._client.get(_TIMEOUT_PATH)
    finally:
        client.close()
