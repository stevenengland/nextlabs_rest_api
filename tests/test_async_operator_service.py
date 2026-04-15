from __future__ import annotations

import asyncio

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._models import Operator
from nextlabs_sdk._cloudaz._operators import AsyncOperatorService

BASE_URL = "https://cloudaz.example.com"


def _make_request(path: str) -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_envelope(data: object) -> httpx.Response:
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
        request=_make_request("/console/api/v1/config/dataType/list"),
    )


def test_async_list_all_returns_operators() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncOperatorService(client)
    response = _make_envelope(
        [
            {"id": 1, "key": "eq", "label": "Equal", "dataType": "STRING"},
        ]
    )
    when(client).get("/console/api/v1/config/dataType/list").thenReturn(response)

    async def run() -> list[Operator]:
        return await service.list_all()

    result = asyncio.run(run())

    assert len(result) == 1
    assert result[0].key == "eq"


def test_async_list_by_type() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncOperatorService(client)
    response = _make_envelope(
        [
            {"id": 3, "key": "gt", "label": "Greater Than", "dataType": "NUMBER"},
        ]
    )
    when(client).get("/console/api/v1/config/dataType/list/NUMBER").thenReturn(response)

    async def run() -> list[Operator]:
        return await service.list_by_type("NUMBER")

    result = asyncio.run(run())

    assert len(result) == 1
    assert result[0].data_type == "NUMBER"


def test_async_list_types() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncOperatorService(client)
    response = _make_envelope(["STRING", "NUMBER"])
    when(client).get("/console/api/v1/config/dataType/types").thenReturn(response)

    async def run() -> list[str]:
        return await service.list_types()

    result = asyncio.run(run())

    assert result == ["STRING", "NUMBER"]
