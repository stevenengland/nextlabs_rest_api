from __future__ import annotations

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._system_config import SystemConfigService
from nextlabs_sdk._cloudaz._system_config_models import SystemConfig
from nextlabs_sdk.exceptions import ServerError

BASE_URL = "https://cloudaz.example.com"
ENDPOINT = "/nextlabs-reporter/api/system-configuration/getUIConfigs"


def _stub(status: int, json_body: object) -> SystemConfigService:
    client = mock(httpx.Client)
    service = SystemConfigService(client)
    response = httpx.Response(
        status,
        json=json_body,
        request=httpx.Request("GET", f"{BASE_URL}/api"),
    )
    when(client).get(ENDPOINT).thenReturn(response)
    return service


def test_get_returns_system_config():
    service = _stub(
        200,
        {
            "skydrm.installed": "false",
            "dashboard.widget.top-policies-and-trends.enabled": "true",
            "application.version": "2025.02",
        },
    )

    config = service.get()

    assert isinstance(config, SystemConfig)
    assert config.get("application.version") == "2025.02"
    assert config.get("skydrm.installed") == "false"
    assert len(config.settings) == 3


def test_get_raises_on_error():
    service = _stub(500, {"message": "Server error"})
    with pytest.raises(ServerError):
        service.get()
