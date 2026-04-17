from __future__ import annotations

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._reporter_audit_log_models import ReporterAuditLogEntry
from nextlabs_sdk._cloudaz._reporter_audit_logs import ReporterAuditLogService
from nextlabs_sdk._pagination import SyncPaginator

BASE_URL = "https://cloudaz.example.com"


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_reporter_envelope(
    content: list[object],
    total_pages: int = 1,
    total_elements: int = 1,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": {
                "content": content,
                "totalPages": total_pages,
                "totalElements": total_elements,
            },
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


def test_search_returns_paginator() -> None:
    client = mock(httpx.Client)
    service = ReporterAuditLogService(client)
    response = _make_reporter_envelope(content=[_make_entry_data()])
    when(client).get(
        "/nextlabs-reporter/api/activity-logs/search",
        params={"page": 0, "size": 20},
    ).thenReturn(response)

    paginator = service.search()

    assert isinstance(paginator, SyncPaginator)
    results = list(paginator)
    assert len(results) == 1
    assert isinstance(results[0], ReporterAuditLogEntry)
    assert results[0].component == "REPORTER"
    assert results[0].msg_code == "audit.export.generated.report"


def test_search_respects_page_size() -> None:
    client = mock(httpx.Client)
    service = ReporterAuditLogService(client)
    response = _make_reporter_envelope(content=[_make_entry_data()])
    when(client).get(
        "/nextlabs-reporter/api/activity-logs/search",
        params={"page": 0, "size": 50},
    ).thenReturn(response)

    results = list(service.search(page_size=50))

    assert len(results) == 1


def test_search_paginates_multiple_pages() -> None:
    client = mock(httpx.Client)
    service = ReporterAuditLogService(client)
    page0 = _make_reporter_envelope(
        content=[_make_entry_data()],
        total_pages=2,
        total_elements=2,
    )
    entry1 = dict(_make_entry_data(), id=1340)
    page1 = _make_reporter_envelope(
        content=[entry1],
        total_pages=2,
        total_elements=2,
    )
    when(client).get(
        "/nextlabs-reporter/api/activity-logs/search",
        params={"page": 0, "size": 20},
    ).thenReturn(page0)
    when(client).get(
        "/nextlabs-reporter/api/activity-logs/search",
        params={"page": 1, "size": 20},
    ).thenReturn(page1)

    results = list(service.search())

    assert len(results) == 2
    assert results[0].id == 1339
    assert results[1].id == 1340
