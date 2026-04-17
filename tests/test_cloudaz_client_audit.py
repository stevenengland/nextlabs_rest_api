from __future__ import annotations

import httpx
from mockito import any as any_value, mock, when

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._cloudaz._async_client import AsyncCloudAzClient
from nextlabs_sdk._cloudaz._audit_logs import (
    AsyncEntityAuditLogService,
    EntityAuditLogService,
)
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._system_config import (
    AsyncSystemConfigService,
    SystemConfigService,
)


def test_cloudaz_client_has_audit_logs() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="u",
        password="p",
    )
    assert isinstance(client.audit_logs, EntityAuditLogService)


def test_cloudaz_client_has_system_config() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="u",
        password="p",
    )
    assert isinstance(client.system_config, SystemConfigService)


def test_async_cloudaz_client_has_audit_logs() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    client = AsyncCloudAzClient(
        base_url="https://cloudaz.example.com",
        username="u",
        password="p",
    )
    assert isinstance(client.audit_logs, AsyncEntityAuditLogService)


def test_async_cloudaz_client_has_system_config() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    client = AsyncCloudAzClient(
        base_url="https://cloudaz.example.com",
        username="u",
        password="p",
    )
    assert isinstance(client.system_config, AsyncSystemConfigService)
