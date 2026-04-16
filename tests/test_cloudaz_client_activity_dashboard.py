from __future__ import annotations

import httpx
from mockito import any as any_value, mock, when

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._cloudaz._async_client import AsyncCloudAzClient
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._activity_logs_service import (
    AsyncReportActivityLogService,
    ReportActivityLogService,
)
from nextlabs_sdk._cloudaz._dashboard import (
    AsyncDashboardService,
    DashboardService,
)


def test_cloudaz_client_has_activity_logs() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="u",
        password="p",
    )
    assert isinstance(client.activity_logs, ReportActivityLogService)


def test_cloudaz_client_has_dashboard() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="u",
        password="p",
    )
    assert isinstance(client.dashboard, DashboardService)


def test_async_cloudaz_client_has_activity_logs() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    client = AsyncCloudAzClient(
        base_url="https://cloudaz.example.com",
        username="u",
        password="p",
    )
    assert isinstance(client.activity_logs, AsyncReportActivityLogService)


def test_async_cloudaz_client_has_dashboard() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    client = AsyncCloudAzClient(
        base_url="https://cloudaz.example.com",
        username="u",
        password="p",
    )
    assert isinstance(client.dashboard, AsyncDashboardService)
