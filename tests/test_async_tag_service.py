from __future__ import annotations

import asyncio

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._models import Tag, TagType
from nextlabs_sdk._cloudaz._tags import AsyncTagService
from nextlabs_sdk._pagination import AsyncPaginator

BASE_URL = "https://cloudaz.example.com"


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_envelope(
    data: object,
    page_no: int = 0,
    total_pages: int = 1,
    total_records: int = 1,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": data,
            "pageNo": page_no,
            "pageSize": 10,
            "totalPages": total_pages,
            "totalNoOfRecords": total_records,
            "additionalAttributes": None,
        },
        request=_make_request(),
    )


def _make_tag_data() -> dict[str, object]:
    return {
        "id": 10,
        "key": "dept",
        "label": "Department",
        "type": "COMPONENT_TAG",
        "status": "ACTIVE",
    }


def test_async_list_returns_paginator() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncTagService(client)
    response = _make_envelope(data=[_make_tag_data()])
    when(client).get(
        "/console/api/v1/config/tags/list/COMPONENT_TAG",
        params={"pageNo": 0},
    ).thenReturn(response)

    paginator = service.list(TagType.COMPONENT)
    assert isinstance(paginator, AsyncPaginator)

    async def collect() -> list[Tag]:
        return [tag async for tag in paginator]

    tags = asyncio.run(collect())
    assert len(tags) == 1
    assert tags[0].key == "dept"


def test_async_get_returns_tag() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncTagService(client)
    response = _make_envelope(data=_make_tag_data())
    when(client).get("/console/api/v1/config/tags/10").thenReturn(response)

    async def run() -> Tag:
        return await service.get(10)

    tag = asyncio.run(run())
    assert tag.id == 10


def test_async_create_returns_id() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncTagService(client)
    response = _make_envelope(data=42)
    when(client).post(
        "/console/api/v1/config/tags/add/POLICY_TAG",
        json={
            "key": "env",
            "label": "Environment",
            "type": "POLICY_TAG",
            "status": "ACTIVE",
        },
    ).thenReturn(response)

    async def run() -> int:
        return await service.create(TagType.POLICY, key="env", label="Environment")

    tag_id = asyncio.run(run())
    assert tag_id == 42


def test_async_delete_succeeds() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncTagService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).delete("/console/api/v1/config/tags/remove/10").thenReturn(response)

    async def run() -> None:
        await service.delete(10)

    asyncio.run(run())
