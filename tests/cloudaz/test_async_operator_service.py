from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._operators import AsyncOperatorService

BASE_URL = "https://cloudaz.example.com"


def _envelope(data: object) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": data,
            "pageNo": 0,
            "pageSize": 10,
            "totalPages": 1,
            "totalNoOfRecords": 1,
            "additionalAttributes": None,
        },
        request=httpx.Request("GET", f"{BASE_URL}/console/api/v1/config/dataType/list"),
    )


@pytest.mark.parametrize(
    "endpoint,data,call,check",
    [
        pytest.param(
            "/console/api/v1/config/dataType/list",
            [{"id": 1, "key": "eq", "label": "Equal", "dataType": "STRING"}],
            lambda svc: svc.list_all(),
            lambda result: len(result) == 1 and result[0].key == "eq",
            id="list_all",
        ),
        pytest.param(
            "/console/api/v1/config/dataType/list/NUMBER",
            [{"id": 3, "key": "gt", "label": "Greater Than", "dataType": "NUMBER"}],
            lambda svc: svc.list_by_type("NUMBER"),
            lambda result: len(result) == 1 and result[0].data_type == "NUMBER",
            id="list_by_type",
        ),
        pytest.param(
            "/console/api/v1/config/dataType/types",
            ["STRING", "NUMBER"],
            lambda svc: svc.list_types(),
            lambda result: result == ["STRING", "NUMBER"],
            id="list_types",
        ),
    ],
)
def test_async_operator_list_endpoints(
    endpoint: str,
    data: object,
    call: Any,
    check: Any,
):
    client = mock(httpx.AsyncClient)
    service = AsyncOperatorService(client)
    when(client).get(endpoint).thenReturn(_envelope(data))

    result = asyncio.run(call(service))

    assert check(result)
