from __future__ import annotations

from unittest.mock import patch

from nextlabs_sdk._cloudaz._audit_logs import (
    AsyncEntityAuditLogService,
    EntityAuditLogService,
)
from nextlabs_sdk._cloudaz._async_client import AsyncCloudAzClient
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._system_config import (
    AsyncSystemConfigService,
    SystemConfigService,
)


@patch("nextlabs_sdk._cloudaz._client.transport_mod.create_http_client")
def test_cloudaz_client_has_audit_logs(mock_create: object) -> None:
    client = CloudAzClient(
        base_url="https://test",
        username="u",
        password="p",
    )
    assert isinstance(client.audit_logs, EntityAuditLogService)


@patch("nextlabs_sdk._cloudaz._client.transport_mod.create_http_client")
def test_cloudaz_client_has_system_config(mock_create: object) -> None:
    client = CloudAzClient(
        base_url="https://test",
        username="u",
        password="p",
    )
    assert isinstance(client.system_config, SystemConfigService)


@patch("nextlabs_sdk._cloudaz._async_client.transport_mod.create_async_http_client")
def test_async_cloudaz_client_has_audit_logs(mock_create: object) -> None:
    client = AsyncCloudAzClient(
        base_url="https://test",
        username="u",
        password="p",
    )
    assert isinstance(client.audit_logs, AsyncEntityAuditLogService)


@patch("nextlabs_sdk._cloudaz._async_client.transport_mod.create_async_http_client")
def test_async_cloudaz_client_has_system_config(mock_create: object) -> None:
    client = AsyncCloudAzClient(
        base_url="https://test",
        username="u",
        password="p",
    )
    assert isinstance(client.system_config, AsyncSystemConfigService)
