from __future__ import annotations

from typing import Any, Callable, cast

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._component_type_models import ComponentType
from nextlabs_sdk._cloudaz._component_type_search import ComponentTypeSearchService
from nextlabs_sdk._cloudaz._search import SavedSearch, SavedSearchType, SearchCriteria
from nextlabs_sdk._pagination import SyncPaginator

BASE_URL = "https://cloudaz.example.com"
_SEARCH = "/console/api/v1/policyModel/search"
_SEARCH_ADD = "/console/api/v1/policyModel/search/add"
_SEARCH_REMOVE = "/console/api/v1/policyModel/search/remove"
_SEARCH_SAVED = "/console/api/v1/policyModel/search/saved"
_SAVED_LIST = "/console/api/v1/policyModel/search/savedlist"


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
        request=httpx.Request("GET", f"{BASE_URL}/api"),
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


@pytest.fixture
def service() -> tuple[ComponentTypeSearchService, httpx.Client]:
    client = cast(httpx.Client, mock(httpx.Client))
    return ComponentTypeSearchService(client), client


def test_search_returns_paginator(
    service: tuple[ComponentTypeSearchService, httpx.Client],
) -> None:
    svc, client = service
    criteria = SearchCriteria().filter_type("RESOURCE")
    when(client).post(_SEARCH, json=criteria.page(0).to_dict()).thenReturn(
        _make_envelope([_make_component_type_data()])
    )

    paginator = svc.search(criteria)

    assert isinstance(paginator, SyncPaginator)
    results = list(paginator)
    assert len(results) == 1
    assert isinstance(results[0], ComponentType)
    assert results[0].name == "Support Tickets"


def test_search_paginates_multiple_pages(
    service: tuple[ComponentTypeSearchService, httpx.Client],
) -> None:
    svc, client = service
    criteria = SearchCriteria().filter_type("RESOURCE")
    ct1 = _make_component_type_data()
    ct2 = dict(
        _make_component_type_data(),
        id=43,
        name="Users",
        shortName="users",
        type="SUBJECT",
    )

    when(client).post(_SEARCH, json=criteria.page(0).to_dict()).thenReturn(
        _make_envelope([ct1], total_pages=2, total_records=2)
    )
    when(client).post(_SEARCH, json=criteria.page(1).to_dict()).thenReturn(
        _make_envelope([ct2], page_no=1, total_pages=2, total_records=2)
    )

    results = list(svc.search(criteria))

    assert len(results) == 2
    assert results[0].name == "Support Tickets"
    assert results[1].name == "Users"


def test_save_search_returns_id(
    service: tuple[ComponentTypeSearchService, httpx.Client],
) -> None:
    svc, client = service
    payload: dict[str, object] = {
        "name": "My Search",
        "desc": "description",
        "type": "POLICY_MODEL_RESOURCE",
        "criteria": {"fields": [], "pageNo": 0, "pageSize": 20},
    }
    when(client).post(_SEARCH_ADD, json=payload).thenReturn(_make_envelope(55))

    assert svc.save_search(payload) == 55


def test_delete_search_succeeds(
    service: tuple[ComponentTypeSearchService, httpx.Client],
) -> None:
    svc, client = service
    response = httpx.Response(200, request=httpx.Request("GET", f"{BASE_URL}/api"))
    when(client).delete(f"{_SEARCH_REMOVE}/10").thenReturn(response)

    svc.delete_search(10)


def test_get_saved_search_returns_model(
    service: tuple[ComponentTypeSearchService, httpx.Client],
) -> None:
    svc, client = service
    when(client).get(f"{_SEARCH_SAVED}/10").thenReturn(
        _make_envelope(_make_saved_search_data())
    )

    ss = svc.get_saved_search(10)

    assert isinstance(ss, SavedSearch)
    assert ss.id == 10
    assert ss.name == "My Search"
    assert ss.type == SavedSearchType.POLICY_MODEL_RESOURCE


@pytest.mark.parametrize(
    "endpoint,call_method",
    [
        pytest.param(
            f"{_SAVED_LIST}/POLICY_MODEL_RESOURCE",
            lambda svc: svc.list_saved_searches("POLICY_MODEL_RESOURCE"),
            id="list-saved-searches",
        ),
        pytest.param(
            f"{_SAVED_LIST}/POLICY_MODEL_RESOURCE/support",
            lambda svc: svc.find_saved_search("POLICY_MODEL_RESOURCE", "support"),
            id="find-saved-search",
        ),
    ],
)
def test_saved_search_paginator(
    service: tuple[ComponentTypeSearchService, httpx.Client],
    endpoint: str,
    call_method: Callable[[ComponentTypeSearchService], Any],
) -> None:
    svc, client = service
    when(client).get(endpoint, params={"pageNo": 0}).thenReturn(
        _make_envelope([_make_saved_search_data()])
    )

    paginator = call_method(svc)

    assert isinstance(paginator, SyncPaginator)
    results = list(paginator)
    assert len(results) == 1
    assert isinstance(results[0], SavedSearch)
