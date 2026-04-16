from __future__ import annotations

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._audit_log_models import (
    AuditLogEntry,
    AuditLogQuery,
    AuditLogUser,
    ExportAuditLogsRequest,
)
from nextlabs_sdk._cloudaz._audit_logs import EntityAuditLogService
from nextlabs_sdk._pagination import SyncPaginator
from nextlabs_sdk.exceptions import ServerError

BASE_URL = "https://cloudaz.example.com"


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


def _make_audit_entry_data() -> dict[str, object]:
    return {
        "id": 12,
        "timestamp": 1718782853766,
        "action": "LOGOUT",
        "actorId": 0,
        "actor": "Administrator",
        "entityType": "AU",
        "entityId": 0,
        "oldValue": None,
        "newValue": '{"Message":"Logged out"}',
    }


def test_search_returns_paginator() -> None:
    client = mock(httpx.Client)
    service = EntityAuditLogService(client)
    query = AuditLogQuery(start_date=100, end_date=200)
    response = _make_reporter_envelope(
        content=[_make_audit_entry_data()],
        total_pages=1,
        total_elements=1,
    )
    when(client).post(
        "/nextlabs-reporter/api/v1/auditLogs/search",
        json={
            "startDate": 100,
            "endDate": 200,
            "pageNumber": 0,
        },
    ).thenReturn(response)

    paginator = service.search(query)

    assert isinstance(paginator, SyncPaginator)
    entries = list(paginator)
    assert len(entries) == 1
    assert isinstance(entries[0], AuditLogEntry)
    assert entries[0].action == "LOGOUT"


def test_search_paginates_multiple_pages() -> None:
    client = mock(httpx.Client)
    service = EntityAuditLogService(client)
    query = AuditLogQuery(start_date=100, end_date=200)
    entry1 = _make_audit_entry_data()
    entry1["id"] = 1
    entry2 = _make_audit_entry_data()
    entry2["id"] = 2

    page0 = _make_reporter_envelope(content=[entry1], total_pages=2, total_elements=2)
    page1 = _make_reporter_envelope(content=[entry2], total_pages=2, total_elements=2)

    when(client).post(
        "/nextlabs-reporter/api/v1/auditLogs/search",
        json={"startDate": 100, "endDate": 200, "pageNumber": 0},
    ).thenReturn(page0)
    when(client).post(
        "/nextlabs-reporter/api/v1/auditLogs/search",
        json={"startDate": 100, "endDate": 200, "pageNumber": 1},
    ).thenReturn(page1)

    entries = list(service.search(query))

    assert len(entries) == 2
    assert entries[0].id == 1
    assert entries[1].id == 2


def test_search_with_filters() -> None:
    client = mock(httpx.Client)
    service = EntityAuditLogService(client)
    query = AuditLogQuery(
        start_date=100,
        end_date=200,
        action="LOGIN",
        entity_type="AU",
        usernames=["admin"],
    )
    response = _make_reporter_envelope(content=[], total_elements=0)
    when(client).post(
        "/nextlabs-reporter/api/v1/auditLogs/search",
        json={
            "startDate": 100,
            "endDate": 200,
            "action": "LOGIN",
            "entityType": "AU",
            "usernames": ["admin"],
            "pageNumber": 0,
        },
    ).thenReturn(response)

    entries = list(service.search(query))

    assert entries == []


def test_export_returns_bytes() -> None:
    client = mock(httpx.Client)
    service = EntityAuditLogService(client)
    request_body = ExportAuditLogsRequest(ids=[5, 10])
    csv_content = b"id,timestamp,action\n5,100,LOGIN\n"
    response = httpx.Response(
        200,
        content=csv_content,
        request=_make_request(),
    )
    when(client).post(
        "/nextlabs-reporter/api/v1/auditLogs/export",
        json={"ids": [5, 10]},
    ).thenReturn(response)

    result = service.export(request_body)

    assert result == csv_content


def test_export_with_query() -> None:
    client = mock(httpx.Client)
    service = EntityAuditLogService(client)
    query = AuditLogQuery(start_date=100, end_date=200)
    request_body = ExportAuditLogsRequest(query=query)
    csv_content = b"id,timestamp,action\n"
    response = httpx.Response(
        200,
        content=csv_content,
        request=_make_request(),
    )
    when(client).post(
        "/nextlabs-reporter/api/v1/auditLogs/export",
        json={"query": {"startDate": 100, "endDate": 200}},
    ).thenReturn(response)

    result = service.export(request_body)

    assert result == csv_content


def test_export_raises_on_error() -> None:
    client = mock(httpx.Client)
    service = EntityAuditLogService(client)
    request_body = ExportAuditLogsRequest(ids=[999])
    response = httpx.Response(
        500,
        json={"statusCode": "5001", "message": "Export error"},
        request=_make_request(),
    )
    when(client).post(
        "/nextlabs-reporter/api/v1/auditLogs/export",
        json={"ids": [999]},
    ).thenReturn(response)

    with pytest.raises(ServerError):
        service.export(request_body)


def test_list_users_returns_user_list() -> None:
    client = mock(httpx.Client)
    service = EntityAuditLogService(client)
    response = _make_data_envelope(
        data=[
            {"firstName": "Test", "lastName": "User", "username": "testuser"},
            {"firstName": "Admin", "lastName": "User", "username": "admin"},
        ]
    )
    when(client).get(
        "/nextlabs-reporter/api/v1/auditLogs/users",
    ).thenReturn(response)

    users = service.list_users()

    assert len(users) == 2
    assert isinstance(users[0], AuditLogUser)
    assert users[0].username == "testuser"
    assert users[1].username == "admin"
