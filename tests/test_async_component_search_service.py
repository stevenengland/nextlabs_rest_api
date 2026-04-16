from __future__ import annotations

import asyncio

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._component_models import (
    ComponentLite,
    ComponentNameEntry,
)
from nextlabs_sdk._cloudaz._component_search import AsyncComponentSearchService
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


def _make_component_lite_data() -> dict[str, object]:
    return {
        "id": 101,
        "folderId": -1,
        "name": "Security Vulnerabilities",
        "fullName": "RESOURCE/Security Vulnerabilities",
        "status": "APPROVED",
        "modelId": 42,
        "modelType": "Support Tickets",
        "group": "RESOURCE",
        "lastUpdatedDate": 1713173211329,
        "createdDate": 1713171640267,
        "ownerId": 0,
        "ownerDisplayName": "Administrator",
        "modifiedById": 0,
        "modifiedBy": "Administrator",
        "hasIncludedIn": False,
        "hasSubComponents": False,
        "tags": [],
        "includedInComponents": [],
        "subComponents": [],
        "deploymentTime": 0,
        "deployed": True,
        "revisionCount": 1,
        "empty": False,
        "version": 2,
        "authorities": [],
        "preCreated": False,
        "referedInPolicies": False,
        "deploymentPending": False,
    }


def _make_saved_search_data() -> dict[str, object]:
    return {
        "id": 10,
        "name": "My Search",
        "desc": "A search",
        "type": "COMPONENT",
        "status": "ACTIVE",
    }


def _make_name_entry_data() -> dict[str, object]:
    return {
        "id": 101,
        "name": "Security Vulnerabilities",
        "empty": False,
        "status": "APPROVED",
        "data": {"policy_model_id": 42, "policy_model_name": "Support Tickets"},
    }


def test_async_search_returns_paginator() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentSearchService(client)
    criteria = SearchCriteria().filter_group("RESOURCE")
    response = _make_envelope(data=[_make_component_lite_data()])
    when(client).post(
        "/console/api/v1/component/search",
        json=criteria.page(0).to_dict(),
    ).thenReturn(response)

    paginator = service.search(criteria)
    assert isinstance(paginator, AsyncPaginator)

    async def collect() -> list[ComponentLite]:
        return [cl async for cl in paginator]

    results = asyncio.run(collect())
    assert len(results) == 1
    assert results[0].name == "Security Vulnerabilities"


def test_async_save_search_returns_id() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentSearchService(client)
    payload: dict[str, object] = {"name": "Search", "type": "COMPONENT", "criteria": {}}
    response = _make_envelope(data=55)
    when(client).post(
        "/console/api/v1/component/search/add",
        json=payload,
    ).thenReturn(response)

    assert asyncio.run(service.save_search(payload)) == 55


def test_async_get_saved_search_returns_model() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentSearchService(client)
    response = _make_envelope(data=_make_saved_search_data())
    when(client).get(
        "/console/api/v1/component/search/saved/10",
    ).thenReturn(response)

    async def run() -> SavedSearch:
        return await service.get_saved_search(10)

    ss = asyncio.run(run())
    assert ss.id == 10


def test_async_list_saved_searches_returns_paginator() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentSearchService(client)
    response = _make_envelope(data=[_make_saved_search_data()])
    when(client).get(
        "/console/api/v1/component/search/savedlist",
        params={"pageNo": 0},
    ).thenReturn(response)

    paginator = service.list_saved_searches()
    assert isinstance(paginator, AsyncPaginator)

    async def collect() -> list[SavedSearch]:
        return [ss async for ss in paginator]

    results = asyncio.run(collect())
    assert len(results) == 1


def test_async_find_saved_search_returns_paginator() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentSearchService(client)
    response = _make_envelope(data=[_make_saved_search_data()])
    when(client).get(
        "/console/api/v1/component/search/savedlist/security",
        params={"pageNo": 0},
    ).thenReturn(response)

    paginator = service.find_saved_search("security")
    assert isinstance(paginator, AsyncPaginator)

    async def collect() -> list[SavedSearch]:
        return [ss async for ss in paginator]

    results = asyncio.run(collect())
    assert len(results) == 1


def test_async_delete_search_succeeds() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentSearchService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).delete(
        "/console/api/v1/component/search/remove/10",
    ).thenReturn(response)

    asyncio.run(service.delete_search(10))


def test_async_list_names_returns_paginator() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentSearchService(client)
    response = _make_envelope(data=[_make_name_entry_data()])
    when(client).get(
        "/console/api/v1/component/search/listNames/RESOURCE",
        params={"pageNo": 0},
    ).thenReturn(response)

    paginator = service.list_names("RESOURCE")
    assert isinstance(paginator, AsyncPaginator)

    async def collect() -> list[ComponentNameEntry]:
        return [entry async for entry in paginator]

    results = asyncio.run(collect())
    assert len(results) == 1
    assert results[0].data is not None
    assert results[0].data.policy_model_id == 42


def test_async_list_names_by_type_returns_paginator() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentSearchService(client)
    response = _make_envelope(data=[_make_name_entry_data()])
    when(client).get(
        "/console/api/v1/component/search/listNames/RESOURCE/Support Tickets",
        params={"pageNo": 0},
    ).thenReturn(response)

    paginator = service.list_names_by_type("RESOURCE", "Support Tickets")
    assert isinstance(paginator, AsyncPaginator)

    async def collect() -> list[ComponentNameEntry]:
        return [entry async for entry in paginator]

    results = asyncio.run(collect())
    assert len(results) == 1
