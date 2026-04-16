from __future__ import annotations

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._system_config import SystemConfigService
from nextlabs_sdk._cloudaz._system_config_models import SystemConfig
from nextlabs_sdk.exceptions import ServerError

BASE_URL = "https://cloudaz.example.com"


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def test_get_returns_system_config() -> None:
    client = mock(httpx.Client)
    service = SystemConfigService(client)
    response = httpx.Response(
        200,
        json={
            "skydrm.installed": "false",
            "dashboard.widget.top-policies-and-trends.enabled": "true",
            "application.version": "2025.02",
        },
        request=_make_request(),
    )
    when(client).get(
        "/nextlabs-reporter/api/system-configuration/getUIConfigs",
    ).thenReturn(response)

    config = service.get()

    assert isinstance(config, SystemConfig)
    assert config.get("application.version") == "2025.02"
    assert config.get("skydrm.installed") == "false"
    assert len(config.settings) == 3


def test_get_raises_on_error() -> None:
    client = mock(httpx.Client)
    service = SystemConfigService(client)
    response = httpx.Response(
        500,
        json={"message": "Server error"},
        request=_make_request(),
    )
    when(client).get(
        "/nextlabs-reporter/api/system-configuration/getUIConfigs",
    ).thenReturn(response)

    with pytest.raises(ServerError):
        service.get()
