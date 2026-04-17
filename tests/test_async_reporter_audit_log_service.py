from __future__ import annotations

import asyncio

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._reporter_audit_log_models import ReporterAuditLogEntry
from nextlabs_sdk._cloudaz._reporter_audit_logs import AsyncReporterAuditLogService
from nextlabs_sdk._pagination import AsyncPaginator

BASE_URL = "https://cloudaz.example.com"


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_reporter_envelope(content: list[object]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": {
                "content": content,
                "totalPages": 1,
                "totalElements": 1,
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


def test_async_search_returns_paginator() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncReporterAuditLogService(client)
    response = _make_reporter_envelope(content=[_make_entry_data()])
    when(client).get(
        "/nextlabs-reporter/api/activity-logs/search",
        params={"page": 0, "size": 20},
    ).thenReturn(response)

    paginator = service.search()

    assert isinstance(paginator, AsyncPaginator)

    async def run() -> list[ReporterAuditLogEntry]:
        return [item async for item in paginator]

    results = asyncio.run(run())
    assert len(results) == 1
    assert isinstance(results[0], ReporterAuditLogEntry)
    assert results[0].component == "REPORTER"
    assert results[0].msg_code == "audit.export.generated.report"
