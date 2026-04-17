from __future__ import annotations

from typing import Any

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._policy_models import PolicyLite
from nextlabs_sdk._cloudaz._policy_search import PolicySearchService
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


def _make_policy_lite_data() -> dict[str, Any]:
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


def _make_saved_search_data() -> dict[str, Any]:
    return {
        "id": 20,
        "name": "My Policy Search",
        "desc": "A search",
        "type": "POLICY",
        "status": "ACTIVE",
    }


@pytest.fixture
def client_service() -> tuple[Any, PolicySearchService]:
    client = mock(httpx.Client)
    return client, PolicySearchService(client)


@pytest.mark.parametrize(
    "path,invoke",
    [
        pytest.param(
            "/console/api/v1/policy/search",
            lambda svc, crit: svc.search(crit),
            id="search",
        ),
        pytest.param(
            "/console/api/v1/policy/search/custom-scope",
            lambda svc, crit: svc.search_named("custom-scope", crit),
            id="search-named",
        ),
    ],
)
def test_search_returns_paginator(
    client_service: tuple[Any, PolicySearchService],
    path: str,
    invoke: Any,
):
    client, service = client_service
    criteria = SearchCriteria().filter_effect_type("allow")
    response = _make_envelope(
        data=[_make_policy_lite_data()],
        total_pages=1,
        total_records=1,
    )
    when(client).post(path, json=criteria.page(0).to_dict()).thenReturn(response)

    paginator = invoke(service, criteria)

    assert isinstance(paginator, SyncPaginator)
    results = list(paginator)
    assert len(results) == 1
    assert isinstance(results[0], PolicyLite)
    assert results[0].name == "Allow IT Ticket Access"
    assert results[0].effect_type == "allow"


def test_search_paginates_multiple_pages(
    client_service: tuple[Any, PolicySearchService],
):
    client, service = client_service
    criteria = SearchCriteria().filter_effect_type("allow")

    lite1 = _make_policy_lite_data()
    lite2 = dict(
        _make_policy_lite_data(),
        id=83,
        name="Allow External Access",
        policyFullName="Allow External Access",
    )

    page0 = _make_envelope(data=[lite1], total_pages=2, total_records=2)
    page1 = _make_envelope(data=[lite2], page_no=1, total_pages=2, total_records=2)

    when(client).post(
        "/console/api/v1/policy/search",
        json=criteria.page(0).to_dict(),
    ).thenReturn(page0)
    when(client).post(
        "/console/api/v1/policy/search",
        json=criteria.page(1).to_dict(),
    ).thenReturn(page1)

    results = list(service.search(criteria))

    assert len(results) == 2
    assert results[0].name == "Allow IT Ticket Access"
    assert results[1].name == "Allow External Access"


def test_save_search_returns_id(client_service: tuple[Any, PolicySearchService]):
    client, service = client_service
    payload: dict[str, object] = {"name": "My Search", "type": "POLICY", "criteria": {}}
    when(client).post(
        "/console/api/v1/policy/search/add",
        json=payload,
    ).thenReturn(_make_envelope(data=55))

    assert service.save_search(payload) == 55


def test_get_saved_search_returns_model(
    client_service: tuple[Any, PolicySearchService],
):
    client, service = client_service
    when(client).get(
        "/console/api/v1/policy/search/saved/20",
    ).thenReturn(_make_envelope(data=_make_saved_search_data()))

    ss = service.get_saved_search(20)

    assert isinstance(ss, SavedSearch)
    assert ss.id == 20
    assert ss.type == SavedSearchType.POLICY


@pytest.mark.parametrize(
    "path,invoke",
    [
        pytest.param(
            "/console/api/v1/policy/search/savedlist",
            lambda svc: svc.list_saved_searches(),
            id="list-saved-searches",
        ),
        pytest.param(
            "/console/api/v1/policy/search/savedlist/security",
            lambda svc: svc.find_saved_search("security"),
            id="find-saved-search",
        ),
    ],
)
def test_saved_search_listing_returns_paginator(
    client_service: tuple[Any, PolicySearchService],
    path: str,
    invoke: Any,
):
    client, service = client_service
    when(client).get(path, params={"pageNo": 0}).thenReturn(
        _make_envelope(data=[_make_saved_search_data()]),
    )

    paginator = invoke(service)

    assert isinstance(paginator, SyncPaginator)
    results = list(paginator)
    assert len(results) == 1
    assert isinstance(results[0], SavedSearch)


def test_delete_search_succeeds(client_service: tuple[Any, PolicySearchService]):
    client, service = client_service
    when(client).delete(
        "/console/api/v1/policy/search/remove/20",
    ).thenReturn(httpx.Response(200, request=_make_request()))

    service.delete_search(20)
