from __future__ import annotations

import asyncio

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._system_config import AsyncSystemConfigService
from nextlabs_sdk.exceptions import ServerError

BASE_URL = "https://cloudaz.example.com"
_ENDPOINT = "/nextlabs-reporter/api/system-configuration/getUIConfigs"


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_service(response: httpx.Response) -> AsyncSystemConfigService:
    client = mock(httpx.AsyncClient)
    service = AsyncSystemConfigService(client)
    when(client).get(_ENDPOINT).thenReturn(response)
    return service


def test_async_get_returns_system_config():
    service = _make_service(
        httpx.Response(
            200,
            json={"skydrm.installed": "false", "application.version": "2025.02"},
            request=_make_request(),
        ),
    )

    config = asyncio.run(service.get())
    assert config.get("application.version") == "2025.02"


def test_async_get_raises_on_error():
    service = _make_service(
        httpx.Response(500, json={"message": "Server error"}, request=_make_request()),
    )

    with pytest.raises(ServerError):
        asyncio.run(service.get())
