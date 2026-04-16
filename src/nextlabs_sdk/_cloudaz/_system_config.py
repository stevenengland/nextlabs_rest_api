from __future__ import annotations

import httpx

from nextlabs_sdk._cloudaz._response import parse_raw
from nextlabs_sdk._cloudaz._system_config_models import SystemConfig

_CONFIG_PATH = "/nextlabs-reporter/api/system-configuration/getUIConfigs"


class SystemConfigService:

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def get(self) -> SystemConfig:
        response = self._client.get(_CONFIG_PATH)
        raw = parse_raw(response)
        return SystemConfig.from_response(raw)


class AsyncSystemConfigService:

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get(self) -> SystemConfig:
        response = await self._client.get(_CONFIG_PATH)
        raw = parse_raw(response)
        return SystemConfig.from_response(raw)
