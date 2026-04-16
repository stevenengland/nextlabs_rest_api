from __future__ import annotations

import asyncio

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._component_type_models import ComponentType
from nextlabs_sdk._cloudaz._component_type_search import AsyncComponentTypeSearchService
from nextlabs_sdk._cloudaz._search import SavedSearch, SearchCriteria
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


def _make_component_type_data() -> dict[str, object]:
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


def _make_saved_search_data() -> dict[str, object]:
    return {
        "id": 10,
        "name": "My Search",
        "desc": "A search",
        "type": "POLICY_MODEL_RESOURCE",
        "status": "ACTIVE",
    }


def test_async_search_returns_paginator() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentTypeSearchService(client)
    criteria = SearchCriteria().filter_type("RESOURCE")
    response = _make_envelope(data=[_make_component_type_data()])
    when(client).post(
        "/console/api/v1/policyModel/search",
        json=criteria.page(0).to_dict(),
    ).thenReturn(response)

    paginator = service.search(criteria)
    assert isinstance(paginator, AsyncPaginator)

    async def collect() -> list[ComponentType]:
        return [ct async for ct in paginator]

    results = asyncio.run(collect())
    assert len(results) == 1
    assert results[0].name == "Support Tickets"


def test_async_save_search_returns_id() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentTypeSearchService(client)
    payload: dict[str, object] = {
        "name": "Search",
        "type": "POLICY_MODEL_RESOURCE",
        "criteria": {},
    }
    response = _make_envelope(data=55)
    when(client).post(
        "/console/api/v1/policyModel/search/add",
        json=payload,
    ).thenReturn(response)

    assert asyncio.run(service.save_search(payload)) == 55


def test_async_delete_search_succeeds() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentTypeSearchService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).delete(
        "/console/api/v1/policyModel/search/remove/10",
    ).thenReturn(response)

    asyncio.run(service.delete_search(10))


def test_async_get_saved_search_returns_model() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentTypeSearchService(client)
    response = _make_envelope(data=_make_saved_search_data())
    when(client).get(
        "/console/api/v1/policyModel/search/saved/10",
    ).thenReturn(response)

    async def run() -> SavedSearch:
        return await service.get_saved_search(10)

    ss = asyncio.run(run())
    assert ss.id == 10
    assert ss.name == "My Search"


def test_async_list_saved_searches_returns_paginator() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentTypeSearchService(client)
    response = _make_envelope(data=[_make_saved_search_data()])
    when(client).get(
        "/console/api/v1/policyModel/search/savedlist/POLICY_MODEL_RESOURCE",
        params={"pageNo": 0},
    ).thenReturn(response)

    paginator = service.list_saved_searches("POLICY_MODEL_RESOURCE")
    assert isinstance(paginator, AsyncPaginator)

    async def collect() -> list[SavedSearch]:
        return [ss async for ss in paginator]

    results = asyncio.run(collect())
    assert len(results) == 1


def test_async_find_saved_search_returns_paginator() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentTypeSearchService(client)
    response = _make_envelope(data=[_make_saved_search_data()])
    when(client).get(
        "/console/api/v1/policyModel/search/savedlist/POLICY_MODEL_RESOURCE/support",
        params={"pageNo": 0},
    ).thenReturn(response)

    paginator = service.find_saved_search("POLICY_MODEL_RESOURCE", "support")
    assert isinstance(paginator, AsyncPaginator)

    async def collect() -> list[SavedSearch]:
        return [ss async for ss in paginator]

    results = asyncio.run(collect())
    assert len(results) == 1
