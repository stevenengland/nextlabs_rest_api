from __future__ import annotations

import httpx
import pytest
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

_BASE_URL = "https://cloudaz.example.com"


def _stub_sync_factory() -> None:
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock(httpx.Client))


def _stub_async_factory() -> None:
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock(httpx.AsyncClient))


@pytest.mark.parametrize(
    "attr,service_cls",
    [
        pytest.param("audit_logs", EntityAuditLogService, id="audit_logs"),
        pytest.param("system_config", SystemConfigService, id="system_config"),
    ],
)
def test_cloudaz_client_has_service(attr, service_cls):
    _stub_sync_factory()
    client = CloudAzClient(base_url=_BASE_URL, username="u", password="p")
    assert isinstance(getattr(client, attr), service_cls)


@pytest.mark.parametrize(
    "attr,service_cls",
    [
        pytest.param("audit_logs", AsyncEntityAuditLogService, id="audit_logs"),
        pytest.param("system_config", AsyncSystemConfigService, id="system_config"),
    ],
)
def test_async_cloudaz_client_has_service(attr, service_cls):
    _stub_async_factory()
    client = AsyncCloudAzClient(base_url=_BASE_URL, username="u", password="p")
    assert isinstance(getattr(client, attr), service_cls)
