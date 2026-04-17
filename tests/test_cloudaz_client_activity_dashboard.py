from __future__ import annotations

import httpx
import pytest
from mockito import any as any_value, mock, when

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._cloudaz._activity_logs_service import (
    AsyncReportActivityLogService,
    ReportActivityLogService,
)
from nextlabs_sdk._cloudaz._async_client import AsyncCloudAzClient
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._dashboard import AsyncDashboardService, DashboardService


def _stub_sync() -> None:
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock(httpx.Client))


def _stub_async() -> None:
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock(httpx.AsyncClient))


@pytest.mark.parametrize(
    "stub,client_cls,attr,service_cls",
    [
        pytest.param(
            _stub_sync,
            CloudAzClient,
            "activity_logs",
            ReportActivityLogService,
            id="sync-activity-logs",
        ),
        pytest.param(
            _stub_sync,
            CloudAzClient,
            "dashboard",
            DashboardService,
            id="sync-dashboard",
        ),
        pytest.param(
            _stub_async,
            AsyncCloudAzClient,
            "activity_logs",
            AsyncReportActivityLogService,
            id="async-activity-logs",
        ),
        pytest.param(
            _stub_async,
            AsyncCloudAzClient,
            "dashboard",
            AsyncDashboardService,
            id="async-dashboard",
        ),
    ],
)
def test_cloudaz_client_exposes_service(stub, client_cls, attr, service_cls):
    stub()
    client = client_cls(
        base_url="https://cloudaz.example.com", username="u", password="p"
    )
    assert isinstance(getattr(client, attr), service_cls)
