from __future__ import annotations

import asyncio
from typing import Any, Awaitable, TypeVar

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._policy_models import PolicyLite
from nextlabs_sdk._cloudaz._policy_search import AsyncPolicySearchService
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
    status_code: int = 200,
    page_no: int = 0,
    page_size: int = 10,
    total_pages: int = 1,
    total_records: int = 1,
) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={
            "statusCode": "1004",
            "message": "Data loaded successfully",
            "data": data,
            "pageNo": page_no,
            "pageSize": page_size,
            "totalPages": total_pages,
            "totalNoOfRecords": total_records,
            "additionalAttributes": None,
        },
        request=_make_request(),
    )


def _policy_lite_data() -> dict[str, Any]:
    return {
        "id": 82,
        "folderId": 3,
        "name": "Allow IT Ticket Access",
        "policyFullName": "Allow IT Ticket Access",
        "status": "APPROVED",
        "effectType": "allow",
        "lastUpdatedDate": 1713173211329,
        "createdDate": 1713171640267,
        "ownerId": 0,
        "ownerDisplayName": "Administrator",
        "modifiedById": 0,
        "modifiedBy": "Administrator",
        "hasParent": False,
        "hasSubPolicies": False,
        "tags": [],
        "subPolicies": [],
        "childNodes": [],
        "authorities": [],
        "deploymentTime": 0,
        "deployed": True,
        "revisionCount": 1,
        "version": 2,
        "deploymentPending": False,
    }


def _saved_search_data() -> dict[str, Any]:
    return {
        "id": 20,
        "name": "My Policy Search",
        "desc": "A search",
        "type": "POLICY",
        "status": "ACTIVE",
    }


def _make_service() -> tuple[Any, AsyncPolicySearchService]:
    client = mock(httpx.AsyncClient)
    return client, AsyncPolicySearchService(client)


def test_async_search_returns_paginator():
    client, service = _make_service()
    criteria = SearchCriteria().filter_effect_type("allow")
    when(client).post(
        "/console/api/v1/policy/search",
        json=criteria.page(0).to_dict(),
    ).thenReturn(_envelope(data=[_policy_lite_data()]))

    paginator = service.search(criteria)
    assert isinstance(paginator, AsyncPaginator)

    results: list[PolicyLite] = _run(_collect_async(paginator))
    assert len(results) == 1
    assert results[0].name == "Allow IT Ticket Access"


def test_async_search_paginates_multiple_pages():
    client, service = _make_service()
    criteria = SearchCriteria().filter_effect_type("allow")

    lite1 = _policy_lite_data()
    lite2 = dict(
        _policy_lite_data(),
        id=83,
        name="Allow External Access",
        policyFullName="Allow External Access",
    )

    page0 = _envelope(data=[lite1], total_pages=2, total_records=2)
    page1 = _envelope(data=[lite2], page_no=1, total_pages=2, total_records=2)

    when(client).post(
        "/console/api/v1/policy/search",
        json=criteria.page(0).to_dict(),
    ).thenReturn(page0)
    when(client).post(
        "/console/api/v1/policy/search",
        json=criteria.page(1).to_dict(),
    ).thenReturn(page1)

    results: list[PolicyLite] = _run(_collect_async(service.search(criteria)))
    assert len(results) == 2
    assert results[0].name == "Allow IT Ticket Access"
    assert results[1].name == "Allow External Access"


def test_async_save_search_returns_id():
    client, service = _make_service()
    payload: dict[str, object] = {
        "name": "My Search",
        "type": "POLICY",
        "criteria": {},
    }
    when(client).post(
        "/console/api/v1/policy/search/add",
        json=payload,
    ).thenReturn(_envelope(data=55))

    assert _run(service.save_search(payload)) == 55


def test_async_get_saved_search_returns_model():
    client, service = _make_service()
    when(client).get(
        "/console/api/v1/policy/search/saved/20",
    ).thenReturn(_envelope(data=_saved_search_data()))

    ss: SavedSearch = _run(service.get_saved_search(20))
    assert ss.id == 20


def test_async_list_saved_searches_returns_paginator():
    client, service = _make_service()
    when(client).get(
        "/console/api/v1/policy/search/savedlist",
        params={"pageNo": 0},
    ).thenReturn(_envelope(data=[_saved_search_data()]))

    paginator = service.list_saved_searches()
    assert isinstance(paginator, AsyncPaginator)

    results: list[SavedSearch] = _run(_collect_async(paginator))
    assert len(results) == 1


def test_async_find_saved_search_returns_paginator():
    client, service = _make_service()
    when(client).get(
        "/console/api/v1/policy/search/savedlist/security",
        params={"pageNo": 0},
    ).thenReturn(_envelope(data=[_saved_search_data()]))

    paginator = service.find_saved_search("security")
    assert isinstance(paginator, AsyncPaginator)

    results: list[SavedSearch] = _run(_collect_async(paginator))
    assert len(results) == 1


def test_async_delete_search_succeeds():
    client, service = _make_service()
    when(client).delete(
        "/console/api/v1/policy/search/remove/20",
    ).thenReturn(httpx.Response(200, request=_make_request()))

    _run(service.delete_search(20))


def test_async_search_named_returns_paginator():
    client, service = _make_service()
    criteria = SearchCriteria().filter_effect_type("allow")
    when(client).post(
        "/console/api/v1/policy/search/custom-scope",
        json=criteria.page(0).to_dict(),
    ).thenReturn(_envelope(data=[_policy_lite_data()]))

    paginator = service.search_named("custom-scope", criteria)
    assert isinstance(paginator, AsyncPaginator)

    results: list[PolicyLite] = _run(_collect_async(paginator))
    assert len(results) == 1
    assert isinstance(results[0], PolicyLite)
    assert results[0].name == "Allow IT Ticket Access"
