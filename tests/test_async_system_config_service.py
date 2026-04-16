from __future__ import annotations

import asyncio

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._system_config import AsyncSystemConfigService
from nextlabs_sdk._cloudaz._system_config_models import SystemConfig
from nextlabs_sdk.exceptions import ServerError

BASE_URL = "https://cloudaz.example.com"


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def test_async_get_returns_system_config() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncSystemConfigService(client)
    response = httpx.Response(
        200,
        json={
            "skydrm.installed": "false",
            "application.version": "2025.02",
        },
        request=_make_request(),
    )
    when(client).get(
        "/nextlabs-reporter/api/system-configuration/getUIConfigs",
    ).thenReturn(response)

    async def run() -> SystemConfig:
        return await service.get()

    config = asyncio.run(run())
    assert isinstance(config, SystemConfig)
    assert config.get("application.version") == "2025.02"


def test_async_get_raises_on_error() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncSystemConfigService(client)
    response = httpx.Response(
        500,
        json={"message": "Server error"},
        request=_make_request(),
    )
    when(client).get(
        "/nextlabs-reporter/api/system-configuration/getUIConfigs",
    ).thenReturn(response)

    async def run() -> SystemConfig:
        return await service.get()

    with pytest.raises(ServerError):
        asyncio.run(run())
