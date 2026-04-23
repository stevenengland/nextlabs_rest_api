from __future__ import annotations

import asyncio
from typing import TypeVar

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._reporter_audit_log_models import ReporterAuditLogEntry
from nextlabs_sdk._cloudaz._reporter_audit_logs import AsyncReporterAuditLogService
from nextlabs_sdk._pagination import AsyncPaginator

BASE_URL = "https://cloudaz.example.com"

T = TypeVar("T")


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_bare_pageable(content: list[object]) -> httpx.Response:
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
            "totalPages": 1,
            "totalElements": 1,
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


def _collect(paginator: AsyncPaginator[T]) -> list[T]:
    async def run() -> list[T]:
        return [item async for item in paginator]

    return asyncio.run(run())


def test_async_search_returns_paginator():
    client = mock(httpx.AsyncClient)
    service = AsyncReporterAuditLogService(client)
    response = _make_bare_pageable(content=[_make_entry_data()])
    when(client).get(
        "/nextlabs-reporter/api/activity-logs/search",
        params={"page": 0, "size": 20},
    ).thenReturn(response)

    paginator = service.search()
    assert isinstance(paginator, AsyncPaginator)

    results = _collect(paginator)
    assert len(results) == 1
    assert isinstance(results[0], ReporterAuditLogEntry)
    assert results[0].component == "REPORTER"
    assert results[0].msg_code == "audit.export.generated.report"


def test_async_search_parses_minimal_top_level_content_without_envelope():
    """Regression: mirrors the sync test — bare Pageable must parse."""
    client = mock(httpx.AsyncClient)
    service = AsyncReporterAuditLogService(client)
    response = httpx.Response(
        200,
        json={
            "content": [_make_entry_data()],
            "totalPages": 1,
            "totalElements": 1,
        },
        request=_make_request(),
    )
    when(client).get(
        "/nextlabs-reporter/api/activity-logs/search",
        params={"page": 0, "size": 20},
    ).thenReturn(response)

    results = _collect(service.search())
    assert len(results) == 1
    assert results[0].id == 1339
