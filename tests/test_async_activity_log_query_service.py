from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine, TypeVar

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._activity_log_query_models import (
    ActivityLogAttribute,
    ActivityLogQuery,
)
from nextlabs_sdk._cloudaz._activity_logs_service import AsyncReportActivityLogService
from nextlabs_sdk._cloudaz._report_models import EnforcementEntry
from nextlabs_sdk._pagination import AsyncPaginator

BASE_URL = "https://cloudaz.example.com"
_BASE_PATH = "/nextlabs-reporter/api/v1/report-activity-logs"

_T = TypeVar("_T")


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("POST", f"{BASE_URL}{path}")


def _reporter_envelope(
    content, total_pages: int = 1, total_elements: int = 1
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


def _data_envelope(data) -> httpx.Response:
    return httpx.Response(
        200,
        json={"statusCode": "1003", "message": "Data found successfully", "data": data},
        request=_make_request(),
    )


def _make_enforcement_row() -> dict[str, object]:
    return {
        "ROW_ID": 2,
        "TIME": "2024-10-07T07:26:14.556+00:00",
        "USER_NAME": "automation_test@nextlabs.com",
        "FROM_RESOURCE_NAME": "file1.txt",
        "POLICY_NAME": "Encryption of Client Data",
        "POLICY_DECISION": "A",
        "ACTION": "SELECT",
        "ACTION_SHORT_CODE": "e3",
    }


def _make_query() -> ActivityLogQuery:
    return ActivityLogQuery(
        from_date=1716825600000,
        to_date=1717516799999,
        policy_decision="AD",
        sort_by="time",
        sort_order="ascending",
    )


def _paged_payload(
    query: ActivityLogQuery, page: int = 0, size: int = 20
) -> dict[str, object]:
    payload = query.model_dump(by_alias=True, exclude_none=True)
    payload["page"] = page
    payload["size"] = size
    return payload


def _make_service() -> tuple[object, AsyncReportActivityLogService]:
    client = mock(httpx.AsyncClient)
    return client, AsyncReportActivityLogService(client)


def _run(coro_factory: Callable[[], Coroutine[Any, Any, _T]]) -> _T:
    return asyncio.run(coro_factory())


def test_async_search_returns_paginator():
    client, service = _make_service()
    query = _make_query()
    when(client).post(_BASE_PATH, json=_paged_payload(query)).thenReturn(
        _reporter_envelope(content=[_make_enforcement_row()]),
    )

    paginator = service.search(query)
    assert isinstance(paginator, AsyncPaginator)
    entries: list[EnforcementEntry] = []

    async def collect() -> None:
        async for entry in paginator:
            entries.append(entry)

    _run(collect)
    assert len(entries) == 1
    assert entries[0].row_id == 2


def test_async_get_by_row_id_returns_attributes():
    client, service = _make_service()
    raw_attrs = [
        {
            "isDynamic": False,
            "dataType": "TIMESTAMP",
            "attrType": "Others",
            "name": "DATE",
            "value": "2024-02-22 06:15:23.177",
        },
        {
            "isDynamic": False,
            "dataType": "STRING",
            "attrType": "User",
            "name": "USER_NAME",
            "value": "John",
        },
    ]
    when(client).get(f"{_BASE_PATH}/42").thenReturn(_data_envelope(raw_attrs))

    attrs = _run(lambda: service.get_by_row_id(42))
    assert len(attrs) == 2
    assert isinstance(attrs[0], ActivityLogAttribute)
    assert attrs[0].name == "DATE"


def test_async_export_returns_bytes():
    client, service = _make_service()
    query = _make_query()
    csv_content = b"ROW_ID,TIME,USER_NAME\n1,2024-01-01,John\n"
    payload = query.model_dump(by_alias=True, exclude_none=True)
    when(client).post(f"{_BASE_PATH}/export", json=payload).thenReturn(
        httpx.Response(200, content=csv_content, request=_make_request()),
    )

    assert _run(lambda: service.export(query)) == csv_content


def test_async_export_by_row_id_returns_bytes():
    client, service = _make_service()
    csv_content = b"DATE,USER_NAME,ACTION\n2024-01-01,John,View\n"
    when(client).post(f"{_BASE_PATH}/99/export").thenReturn(
        httpx.Response(200, content=csv_content, request=_make_request()),
    )

    assert _run(lambda: service.export_by_row_id(99)) == csv_content
