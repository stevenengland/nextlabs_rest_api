from __future__ import annotations

from typing import Union

import httpx
import pytest
from mockito import any as any_value, mock, when

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._cloudaz._async_client import AsyncCloudAzClient
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._reports import (
    AsyncPolicyActivityReportService,
    PolicyActivityReportService,
)


@pytest.mark.parametrize(
    "is_async,service_cls",
    [
        pytest.param(False, PolicyActivityReportService, id="sync"),
        pytest.param(True, AsyncPolicyActivityReportService, id="async"),
    ],
)
def test_cloudaz_client_has_reports(is_async: bool, service_cls: type) -> None:
    client: Union[CloudAzClient, AsyncCloudAzClient]
    if is_async:
        mock_async = mock(httpx.AsyncClient)
        when(transport_mod).create_async_http_client(
            base_url=any_value(),
            auth=any_value(),
            http_config=any_value(),
        ).thenReturn(mock_async)
        client = AsyncCloudAzClient(
            base_url="https://cloudaz.example.com",
            username="u",
            password="p",
        )
    else:
        mock_sync = mock(httpx.Client)
        when(transport_mod).create_http_client(
            base_url=any_value(),
            auth=any_value(),
            http_config=any_value(),
        ).thenReturn(mock_sync)
        client = CloudAzClient(
            base_url="https://cloudaz.example.com",
            username="u",
            password="p",
        )
    assert isinstance(client.reports, service_cls)
