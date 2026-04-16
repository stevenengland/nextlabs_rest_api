from __future__ import annotations

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._activity_log_query_models import (
    ActivityLogAttribute,
    ActivityLogQuery,
)
from nextlabs_sdk._cloudaz._activity_logs_service import ReportActivityLogService
from nextlabs_sdk._cloudaz._report_models import EnforcementEntry
from nextlabs_sdk._pagination import SyncPaginator

BASE_URL = "https://cloudaz.example.com"
_BASE_PATH = "/nextlabs-reporter/api/v1/report-activity-logs"


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("POST", f"{BASE_URL}{path}")


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


def _make_data_envelope(data: object) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": data,
        },
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


# --- search ---


def test_search_returns_paginator() -> None:
    client = mock(httpx.Client)
    service = ReportActivityLogService(client)
    query = _make_query()

    response = _make_reporter_envelope(
        content=[_make_enforcement_row()],
        total_pages=1,
        total_elements=1,
    )
    payload = query.model_dump(by_alias=True, exclude_none=True)
    payload["page"] = 0
    payload["size"] = 20
    when(client).post(_BASE_PATH, json=payload).thenReturn(response)

    paginator = service.search(query)
    assert isinstance(paginator, SyncPaginator)
    entries = list(paginator)
    assert len(entries) == 1
    assert isinstance(entries[0], EnforcementEntry)
    assert entries[0].row_id == 2


def test_search_paginates_multiple_pages() -> None:
    client = mock(httpx.Client)
    service = ReportActivityLogService(client)
    query = _make_query()

    row1 = _make_enforcement_row()
    row1["ROW_ID"] = 1
    row2 = _make_enforcement_row()
    row2["ROW_ID"] = 2

    page0 = _make_reporter_envelope(content=[row1], total_pages=2, total_elements=2)
    page1 = _make_reporter_envelope(content=[row2], total_pages=2, total_elements=2)

    payload0 = query.model_dump(by_alias=True, exclude_none=True)
    payload0["page"] = 0
    payload0["size"] = 20
    payload1 = query.model_dump(by_alias=True, exclude_none=True)
    payload1["page"] = 1
    payload1["size"] = 20

    when(client).post(_BASE_PATH, json=payload0).thenReturn(page0)
    when(client).post(_BASE_PATH, json=payload1).thenReturn(page1)

    entries = list(service.search(query))
    assert len(entries) == 2
    assert entries[0].row_id == 1
    assert entries[1].row_id == 2


# --- get_by_row_id ---


def test_get_by_row_id_returns_attributes() -> None:
    client = mock(httpx.Client)
    service = ReportActivityLogService(client)

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
    response = _make_data_envelope(raw_attrs)
    when(client).get(f"{_BASE_PATH}/42").thenReturn(response)

    attrs = service.get_by_row_id(42)
    assert len(attrs) == 2
    assert isinstance(attrs[0], ActivityLogAttribute)
    assert attrs[0].name == "DATE"
    assert attrs[0].data_type == "TIMESTAMP"
    assert attrs[1].name == "USER_NAME"
    assert attrs[1].value == "John"


# --- export ---


def test_export_returns_bytes() -> None:
    client = mock(httpx.Client)
    service = ReportActivityLogService(client)
    query = _make_query()

    csv_content = b"ROW_ID,TIME,USER_NAME\n1,2024-01-01,John\n"
    payload = query.model_dump(by_alias=True, exclude_none=True)
    response = httpx.Response(200, content=csv_content, request=_make_request())
    when(client).post(f"{_BASE_PATH}/export", json=payload).thenReturn(response)

    result = service.export(query)
    assert result == csv_content


# --- export_by_row_id ---


def test_export_by_row_id_returns_bytes() -> None:
    client = mock(httpx.Client)
    service = ReportActivityLogService(client)

    csv_content = b"DATE,USER_NAME,ACTION\n2024-01-01,John,View\n"
    response = httpx.Response(200, content=csv_content, request=_make_request())
    when(client).post(f"{_BASE_PATH}/99/export").thenReturn(response)

    result = service.export_by_row_id(99)
    assert result == csv_content
