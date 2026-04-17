from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine, TypeVar

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._models import Tag, TagType
from nextlabs_sdk._cloudaz._tags import AsyncTagService
from nextlabs_sdk._pagination import AsyncPaginator

BASE_URL = "https://cloudaz.example.com"

_T = TypeVar("_T")


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_envelope(
    data,
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


def _make_service() -> tuple[object, AsyncTagService]:
    client = mock(httpx.AsyncClient)
    return client, AsyncTagService(client)


def _run(coro_factory: Callable[[], Coroutine[Any, Any, _T]]) -> _T:
    return asyncio.run(coro_factory())


def test_async_list_returns_paginator():
    client, service = _make_service()
    when(client).get(
        "/console/api/v1/config/tags/list/COMPONENT_TAG",
        params={"pageNo": 0},
    ).thenReturn(_make_envelope(data=[_make_tag_data()]))

    paginator = service.list(TagType.COMPONENT)
    assert isinstance(paginator, AsyncPaginator)

    async def collect() -> list[Tag]:
        return [tag async for tag in paginator]

    tags = _run(collect)
    assert len(tags) == 1
    assert tags[0].key == "dept"


def test_async_get_returns_tag():
    client, service = _make_service()
    when(client).get("/console/api/v1/config/tags/10").thenReturn(
        _make_envelope(data=_make_tag_data()),
    )

    tag = _run(lambda: service.get(10))
    assert tag.id == 10


def test_async_create_returns_id():
    client, service = _make_service()
    when(client).post(
        "/console/api/v1/config/tags/add/POLICY_TAG",
        json={
            "key": "env",
            "label": "Environment",
            "type": "POLICY_TAG",
            "status": "ACTIVE",
        },
    ).thenReturn(_make_envelope(data=42))

    tag_id = _run(
        lambda: service.create(TagType.POLICY, key="env", label="Environment")
    )
    assert tag_id == 42


def test_async_delete_succeeds():
    client, service = _make_service()
    when(client).delete("/console/api/v1/config/tags/remove/10").thenReturn(
        httpx.Response(200, request=_make_request()),
    )

    _run(lambda: service.delete(10))
