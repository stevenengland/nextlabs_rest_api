from __future__ import annotations

import asyncio
from typing import Any, Awaitable, TypeVar

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._component_type_models import ComponentType
from nextlabs_sdk._cloudaz._component_type_search import AsyncComponentTypeSearchService
from nextlabs_sdk._cloudaz._search import SavedSearch, SearchCriteria
from nextlabs_sdk._pagination import AsyncPaginator

BASE_URL = "https://cloudaz.example.com"

T = TypeVar("T")


def _run(coro: Awaitable[T]) -> T:
    return asyncio.run(coro)  # type: ignore[arg-type]


async def _collect_async(paginator: AsyncPaginator[T]) -> list[T]:
    return [item async for item in paginator]


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _envelope(
    data: object,
    page_no: int = 0,
    total_pages: int = 1,
    total_records: int = 1,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "statusCode": "1004",
            "message": "Data loaded successfully",
            "data": data,
            "pageNo": page_no,
            "pageSize": 10,
            "totalPages": total_pages,
            "totalNoOfRecords": total_records,
            "additionalAttributes": None,
        },
        request=_make_request(),
    )


def _component_type_data() -> dict[str, object]:
    return {
        "id": 42,
        "name": "Support Tickets",
        "shortName": "support_tickets",
        "type": "RESOURCE",
        "status": "ACTIVE",
        "tags": [],
        "attributes": [],
        "actions": [],
        "obligations": [],
        "version": 1,
        "ownerId": 0,
        "ownerDisplayName": None,
        "createdDate": 0,
        "lastUpdatedDate": 1713166450257,
        "modifiedById": 0,
        "modifiedBy": None,
    }


def _saved_search_data() -> dict[str, object]:
    return {
        "id": 10,
        "name": "My Search",
        "desc": "A search",
        "type": "POLICY_MODEL_RESOURCE",
        "status": "ACTIVE",
    }


def _make_service() -> tuple[Any, AsyncComponentTypeSearchService]:
    client = mock(httpx.AsyncClient)
    return client, AsyncComponentTypeSearchService(client)


def test_async_search_returns_paginator():
    client, service = _make_service()
    criteria = SearchCriteria().filter_type("RESOURCE")
    when(client).post(
        "/console/api/v1/policyModel/search",
        json=criteria.page(0).to_dict(),
    ).thenReturn(_envelope(data=[_component_type_data()]))

    paginator = service.search(criteria)
    assert isinstance(paginator, AsyncPaginator)

    results: list[ComponentType] = _run(_collect_async(paginator))
    assert len(results) == 1
    assert results[0].name == "Support Tickets"


def test_async_save_search_returns_id():
    client, service = _make_service()
    payload: dict[str, object] = {
        "name": "Search",
        "type": "POLICY_MODEL_RESOURCE",
        "criteria": {},
    }
    when(client).post(
        "/console/api/v1/policyModel/search/add",
        json=payload,
    ).thenReturn(_envelope(data=55))

    assert _run(service.save_search(payload)) == 55


def test_async_delete_search_succeeds():
    client, service = _make_service()
    when(client).delete(
        "/console/api/v1/policyModel/search/remove/10",
    ).thenReturn(httpx.Response(200, request=_make_request()))

    _run(service.delete_search(10))


def test_async_get_saved_search_returns_model():
    client, service = _make_service()
    when(client).get(
        "/console/api/v1/policyModel/search/saved/10",
    ).thenReturn(_envelope(data=_saved_search_data()))

    ss: SavedSearch = _run(service.get_saved_search(10))
    assert ss.id == 10
    assert ss.name == "My Search"


def test_async_list_saved_searches_returns_paginator():
    client, service = _make_service()
    when(client).get(
        "/console/api/v1/policyModel/search/savedlist/POLICY_MODEL_RESOURCE",
        params={"pageNo": 0},
    ).thenReturn(_envelope(data=[_saved_search_data()]))

    paginator = service.list_saved_searches("POLICY_MODEL_RESOURCE")
    assert isinstance(paginator, AsyncPaginator)

    results: list[SavedSearch] = _run(_collect_async(paginator))
    assert len(results) == 1


def test_async_find_saved_search_returns_paginator():
    client, service = _make_service()
    when(client).get(
        "/console/api/v1/policyModel/search/savedlist/POLICY_MODEL_RESOURCE/support",
        params={"pageNo": 0},
    ).thenReturn(_envelope(data=[_saved_search_data()]))

    paginator = service.find_saved_search("POLICY_MODEL_RESOURCE", "support")
    assert isinstance(paginator, AsyncPaginator)

    results: list[SavedSearch] = _run(_collect_async(paginator))
    assert len(results) == 1
