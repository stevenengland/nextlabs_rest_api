from __future__ import annotations

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._reporter_audit_log_models import ReporterAuditLogEntry
from nextlabs_sdk._cloudaz._reporter_audit_logs import ReporterAuditLogService
from nextlabs_sdk._pagination import SyncPaginator

BASE_URL = "https://cloudaz.example.com"
SEARCH_URL = "/nextlabs-reporter/api/activity-logs/search"


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_bare_pageable(
    content: list[object],
    total_pages: int = 1,
    total_elements: int = 1,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "content": content,
            "pageable": {
                "sort": {"unsorted": False, "sorted": True, "empty": False},
                "pageSize": 20,
                "pageNumber": 0,
                "offset": 0,
                "paged": True,
                "unpaged": False,
            },
            "totalPages": total_pages,
            "totalElements": total_elements,
            "last": True,
            "sort": {"unsorted": False, "sorted": True, "empty": False},
            "first": True,
            "numberOfElements": len(content),
            "size": 20,
            "number": 0,
            "empty": not content,
        },
        request=_make_request(),
    )


def _make_entry_data() -> dict[str, object]:
    return {
        "id": 1339,
        "component": "REPORTER",
        "createdBy": 0,
        "createdDate": 1746587919483,
        "hidden": False,
        "lastUpdated": 1746587919483,
        "lastUpdatedBy": 0,
        "msgCode": "audit.export.generated.report",
        "msgParams": '["Test Report"]',
        "ownerDisplayName": "Administrator",
        "activityMsg": "exported {0} generated report",
    }


@pytest.mark.parametrize(
    "page_size,kwargs",
    [
        pytest.param(20, {}, id="default"),
        pytest.param(50, {"page_size": 50}, id="custom-page-size"),
    ],
)
def test_search_honors_page_size(page_size, kwargs):
    client = mock(httpx.Client)
    service = ReporterAuditLogService(client)
    response = _make_bare_pageable(content=[_make_entry_data()])
    when(client).get(
        SEARCH_URL,
        params={"page": 0, "size": page_size},
    ).thenReturn(response)

    paginator = service.search(**kwargs)

    assert isinstance(paginator, SyncPaginator)
    results = list(paginator)
    assert len(results) == 1
    assert isinstance(results[0], ReporterAuditLogEntry)
    assert results[0].component == "REPORTER"
    assert results[0].msg_code == "audit.export.generated.report"


def test_search_paginates_multiple_pages():
    client = mock(httpx.Client)
    service = ReporterAuditLogService(client)
    page0 = _make_bare_pageable(
        content=[_make_entry_data()],
        total_pages=2,
        total_elements=2,
    )
    entry1 = dict(_make_entry_data(), id=1340)
    page1 = _make_bare_pageable(
        content=[entry1],
        total_pages=2,
        total_elements=2,
    )
    when(client).get(SEARCH_URL, params={"page": 0, "size": 20}).thenReturn(page0)
    when(client).get(SEARCH_URL, params={"page": 1, "size": 20}).thenReturn(page1)

    results = list(service.search())

    assert len(results) == 2
    assert results[0].id == 1339
    assert results[1].id == 1340


def test_search_parses_minimal_top_level_content_without_envelope():
    """Regression: the live server returns a bare Spring Pageable with no
    ``statusCode`` / ``data`` envelope. The parser must not demand one."""
    client = mock(httpx.Client)
    service = ReporterAuditLogService(client)
    response = httpx.Response(
        200,
        json={
            "content": [_make_entry_data()],
            "totalPages": 1,
            "totalElements": 1,
        },
        request=_make_request(),
    )
    when(client).get(SEARCH_URL, params={"page": 0, "size": 20}).thenReturn(response)

    results = list(service.search())

    assert len(results) == 1
    assert results[0].id == 1339
