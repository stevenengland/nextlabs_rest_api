from __future__ import annotations

import httpx
from mockito import mock, when
import pytest

from nextlabs_sdk._cloudaz._component_models import (
    ComponentLite,
    ComponentNameEntry,
    ComponentStatus,
)
from nextlabs_sdk._cloudaz._component_search import ComponentSearchService
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


def _component_lite(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
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
    base.update(overrides)
    return base


def _saved_search_data() -> dict[str, object]:
    return {
        "id": 10,
        "name": "My Component Search",
        "desc": "A search",
        "type": "COMPONENT",
        "status": "ACTIVE",
    }


def _name_entry_data() -> dict[str, object]:
    return {
        "id": 101,
        "name": "Security Vulnerabilities",
        "empty": False,
        "status": "APPROVED",
        "data": {"policy_model_id": 42, "policy_model_name": "Support Tickets"},
    }


@pytest.fixture
def client():
    return mock(httpx.Client)


@pytest.fixture
def service(client):
    return ComponentSearchService(client)


def test_search_returns_paginator(client, service):
    criteria = SearchCriteria().filter_group("RESOURCE")
    when(client).post(
        "/console/api/v1/component/search",
        json=criteria.page(0).to_dict(),
    ).thenReturn(_make_envelope(data=[_component_lite()]))

    paginator = service.search(criteria)

    assert isinstance(paginator, SyncPaginator)
    results = list(paginator)
    assert len(results) == 1
    assert isinstance(results[0], ComponentLite)
    assert results[0].name == "Security Vulnerabilities"
    assert results[0].status == ComponentStatus.APPROVED


def test_search_paginates_multiple_pages(client, service):
    criteria = SearchCriteria().filter_group("RESOURCE")
    lite1 = _component_lite()
    lite2 = _component_lite(
        id=102,
        name="Tickets in Product Area",
        fullName="RESOURCE/Tickets in Product Area",
    )
    page0 = _make_envelope(data=[lite1], total_pages=2, total_records=2)
    page1 = _make_envelope(data=[lite2], page_no=1, total_pages=2, total_records=2)

    when(client).post(
        "/console/api/v1/component/search",
        json=criteria.page(0).to_dict(),
    ).thenReturn(page0)
    when(client).post(
        "/console/api/v1/component/search",
        json=criteria.page(1).to_dict(),
    ).thenReturn(page1)

    results = list(service.search(criteria))

    assert len(results) == 2
    assert results[0].name == "Security Vulnerabilities"
    assert results[1].name == "Tickets in Product Area"


def test_save_search_returns_id(client, service):
    payload: dict[str, object] = {
        "name": "My Search",
        "type": "COMPONENT",
        "criteria": {},
    }
    when(client).post(
        "/console/api/v1/component/search/add",
        json=payload,
    ).thenReturn(_make_envelope(data=55))

    assert service.save_search(payload) == 55


def test_get_saved_search_returns_model(client, service):
    when(client).get(
        "/console/api/v1/component/search/saved/10",
    ).thenReturn(_make_envelope(data=_saved_search_data()))

    ss = service.get_saved_search(10)

    assert isinstance(ss, SavedSearch)
    assert ss.id == 10
    assert ss.type == SavedSearchType.COMPONENT


@pytest.mark.parametrize(
    "call,url",
    [
        pytest.param(
            lambda s: s.list_saved_searches(),
            "/console/api/v1/component/search/savedlist",
            id="list-saved-searches",
        ),
        pytest.param(
            lambda s: s.find_saved_search("security"),
            "/console/api/v1/component/search/savedlist/security",
            id="find-saved-search",
        ),
    ],
)
def test_saved_search_paginators(client, service, call, url):
    when(client).get(url, params={"pageNo": 0}).thenReturn(
        _make_envelope(data=[_saved_search_data()]),
    )

    paginator = call(service)

    assert isinstance(paginator, SyncPaginator)
    results = list(paginator)
    assert len(results) == 1
    assert isinstance(results[0], SavedSearch)


def test_delete_search_succeeds(client, service):
    when(client).delete(
        "/console/api/v1/component/search/remove/10",
    ).thenReturn(httpx.Response(200, request=_make_request()))

    service.delete_search(10)


def test_list_names_returns_paginator(client, service):
    when(client).get(
        "/console/api/v1/component/search/listNames/RESOURCE",
        params={"pageNo": 0},
    ).thenReturn(_make_envelope(data=[_name_entry_data()]))

    paginator = service.list_names("RESOURCE")

    assert isinstance(paginator, SyncPaginator)
    results = list(paginator)
    assert len(results) == 1
    assert isinstance(results[0], ComponentNameEntry)
    assert results[0].name == "Security Vulnerabilities"
    assert results[0].data is not None
    assert results[0].data.policy_model_id == 42


def test_list_names_by_type_returns_paginator(client, service):
    when(client).get(
        "/console/api/v1/component/search/listNames/RESOURCE/Support Tickets",
        params={"pageNo": 0},
    ).thenReturn(_make_envelope(data=[_name_entry_data()]))

    paginator = service.list_names_by_type("RESOURCE", "Support Tickets")

    assert isinstance(paginator, SyncPaginator)
    results = list(paginator)
    assert len(results) == 1
