from __future__ import annotations

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._component_type_models import ComponentType
from nextlabs_sdk._cloudaz._component_type_search import ComponentTypeSearchService
from nextlabs_sdk._cloudaz._search import SavedSearch, SavedSearchType, SearchCriteria
from nextlabs_sdk._pagination import SyncPaginator

BASE_URL = "https://cloudaz.example.com"


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_envelope(
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


def test_search_returns_paginator() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeSearchService(client)
    criteria = SearchCriteria().filter_type("RESOURCE")
    response = _make_envelope(
        data=[_make_component_type_data()],
        total_pages=1,
        total_records=1,
    )
    when(client).post(
        "/console/api/v1/policyModel/search",
        json=criteria.page(0).to_dict(),
    ).thenReturn(response)

    paginator = service.search(criteria)

    assert isinstance(paginator, SyncPaginator)
    results = list(paginator)
    assert len(results) == 1
    assert isinstance(results[0], ComponentType)
    assert results[0].name == "Support Tickets"


def test_search_paginates_multiple_pages() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeSearchService(client)
    criteria = SearchCriteria().filter_type("RESOURCE")

    ct1 = _make_component_type_data()
    ct2 = dict(
        _make_component_type_data(),
        id=43,
        name="Users",
        shortName="users",
        type="SUBJECT",
    )

    page0 = _make_envelope(data=[ct1], total_pages=2, total_records=2)
    page1 = _make_envelope(data=[ct2], page_no=1, total_pages=2, total_records=2)

    when(client).post(
        "/console/api/v1/policyModel/search",
        json=criteria.page(0).to_dict(),
    ).thenReturn(page0)
    when(client).post(
        "/console/api/v1/policyModel/search",
        json=criteria.page(1).to_dict(),
    ).thenReturn(page1)

    results = list(service.search(criteria))

    assert len(results) == 2
    assert results[0].name == "Support Tickets"
    assert results[1].name == "Users"


def test_save_search_returns_id() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeSearchService(client)
    payload: dict[str, object] = {
        "name": "My Search",
        "desc": "description",
        "type": "POLICY_MODEL_RESOURCE",
        "criteria": {"fields": [], "pageNo": 0, "pageSize": 20},
    }
    response = _make_envelope(data=55)
    when(client).post(
        "/console/api/v1/policyModel/search/add",
        json=payload,
    ).thenReturn(response)

    result = service.save_search(payload)

    assert result == 55


def test_delete_search_succeeds() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeSearchService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).delete(
        "/console/api/v1/policyModel/search/remove/10",
    ).thenReturn(response)

    service.delete_search(10)


def test_get_saved_search_returns_model() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeSearchService(client)
    response = _make_envelope(data=_make_saved_search_data())
    when(client).get(
        "/console/api/v1/policyModel/search/saved/10",
    ).thenReturn(response)

    ss = service.get_saved_search(10)

    assert isinstance(ss, SavedSearch)
    assert ss.id == 10
    assert ss.name == "My Search"
    assert ss.type == SavedSearchType.POLICY_MODEL_RESOURCE


def test_list_saved_searches_returns_paginator() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeSearchService(client)
    response = _make_envelope(
        data=[_make_saved_search_data()],
        total_pages=1,
        total_records=1,
    )
    when(client).get(
        "/console/api/v1/policyModel/search/savedlist/POLICY_MODEL_RESOURCE",
        params={"pageNo": 0},
    ).thenReturn(response)

    paginator = service.list_saved_searches("POLICY_MODEL_RESOURCE")

    assert isinstance(paginator, SyncPaginator)
    results = list(paginator)
    assert len(results) == 1
    assert isinstance(results[0], SavedSearch)


def test_find_saved_search_returns_paginator() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeSearchService(client)
    response = _make_envelope(
        data=[_make_saved_search_data()],
        total_pages=1,
        total_records=1,
    )
    when(client).get(
        "/console/api/v1/policyModel/search/savedlist/POLICY_MODEL_RESOURCE/support",
        params={"pageNo": 0},
    ).thenReturn(response)

    paginator = service.find_saved_search("POLICY_MODEL_RESOURCE", "support")

    assert isinstance(paginator, SyncPaginator)
    results = list(paginator)
    assert len(results) == 1
