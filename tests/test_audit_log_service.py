from __future__ import annotations

from typing import cast

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
_SEARCH = "/nextlabs-reporter/api/v1/auditLogs/search"
_EXPORT = "/nextlabs-reporter/api/v1/auditLogs/export"
_USERS = "/nextlabs-reporter/api/v1/auditLogs/users"


def _request() -> httpx.Request:
    return httpx.Request("POST", f"{BASE_URL}/api")


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
        request=_request(),
    )


def _make_data_envelope(data: object) -> httpx.Response:
    return httpx.Response(
        200,
        json={"statusCode": "1003", "message": "Data found successfully", "data": data},
        request=_request(),
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


@pytest.fixture
def service() -> tuple[EntityAuditLogService, httpx.Client]:
    client = cast(httpx.Client, mock(httpx.Client))
    return EntityAuditLogService(client), client


def test_search_returns_paginator(
    service: tuple[EntityAuditLogService, httpx.Client],
) -> None:
    svc, client = service
    query = AuditLogQuery(start_date=100, end_date=200)
    when(client).post(
        _SEARCH,
        json={"startDate": 100, "endDate": 200, "pageNumber": 0},
    ).thenReturn(_make_reporter_envelope([_make_audit_entry_data()]))

    paginator = svc.search(query)

    assert isinstance(paginator, SyncPaginator)
    entries = list(paginator)
    assert len(entries) == 1
    assert isinstance(entries[0], AuditLogEntry)
    assert entries[0].action == "LOGOUT"


def test_search_paginates_multiple_pages(
    service: tuple[EntityAuditLogService, httpx.Client],
) -> None:
    svc, client = service
    query = AuditLogQuery(start_date=100, end_date=200)
    entry1 = _make_audit_entry_data()
    entry1["id"] = 1
    entry2 = _make_audit_entry_data()
    entry2["id"] = 2

    when(client).post(
        _SEARCH,
        json={"startDate": 100, "endDate": 200, "pageNumber": 0},
    ).thenReturn(_make_reporter_envelope([entry1], total_pages=2, total_elements=2))
    when(client).post(
        _SEARCH,
        json={"startDate": 100, "endDate": 200, "pageNumber": 1},
    ).thenReturn(_make_reporter_envelope([entry2], total_pages=2, total_elements=2))

    entries = list(svc.search(query))

    assert len(entries) == 2
    assert entries[0].id == 1
    assert entries[1].id == 2


def test_search_with_filters(
    service: tuple[EntityAuditLogService, httpx.Client],
) -> None:
    svc, client = service
    query = AuditLogQuery(
        start_date=100,
        end_date=200,
        action="LOGIN",
        entity_type="AU",
        usernames=["admin"],
    )
    when(client).post(
        _SEARCH,
        json={
            "startDate": 100,
            "endDate": 200,
            "action": "LOGIN",
            "entityType": "AU",
            "usernames": ["admin"],
            "pageNumber": 0,
        },
    ).thenReturn(_make_reporter_envelope([], total_elements=0))

    assert list(svc.search(query)) == []


@pytest.mark.parametrize(
    "request_body,expected_json,csv_content",
    [
        pytest.param(
            ExportAuditLogsRequest(ids=[5, 10]),
            {"ids": [5, 10]},
            b"id,timestamp,action\n5,100,LOGIN\n",
            id="ids",
        ),
        pytest.param(
            ExportAuditLogsRequest(query=AuditLogQuery(start_date=100, end_date=200)),
            {"query": {"startDate": 100, "endDate": 200}},
            b"id,timestamp,action\n",
            id="query",
        ),
    ],
)
def test_export_returns_bytes(
    service: tuple[EntityAuditLogService, httpx.Client],
    request_body: ExportAuditLogsRequest,
    expected_json: dict[str, object],
    csv_content: bytes,
) -> None:
    svc, client = service
    when(client).post(_EXPORT, json=expected_json).thenReturn(
        httpx.Response(200, content=csv_content, request=_request())
    )

    assert svc.export(request_body) == csv_content


def test_export_raises_on_error(
    service: tuple[EntityAuditLogService, httpx.Client],
) -> None:
    svc, client = service
    request_body = ExportAuditLogsRequest(ids=[999])
    when(client).post(_EXPORT, json={"ids": [999]}).thenReturn(
        httpx.Response(
            500,
            json={"statusCode": "5001", "message": "Export error"},
            request=_request(),
        )
    )

    with pytest.raises(ServerError):
        svc.export(request_body)


def test_list_users_returns_user_list(
    service: tuple[EntityAuditLogService, httpx.Client],
) -> None:
    svc, client = service
    when(client).get(_USERS).thenReturn(
        _make_data_envelope(
            [
                {"firstName": "Test", "lastName": "User", "username": "testuser"},
                {"firstName": "Admin", "lastName": "User", "username": "admin"},
            ]
        )
    )

    users = svc.list_users()

    assert len(users) == 2
    assert isinstance(users[0], AuditLogUser)
    assert users[0].username == "testuser"
    assert users[1].username == "admin"
