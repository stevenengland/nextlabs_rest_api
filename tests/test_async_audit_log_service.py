from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._audit_log_models import (
    AuditLogEntry,
    AuditLogQuery,
    AuditLogUser,
    ExportAuditLogsRequest,
)
from nextlabs_sdk._cloudaz._audit_logs import AsyncEntityAuditLogService
from nextlabs_sdk._pagination import AsyncPaginator
from nextlabs_sdk.exceptions import ServerError

BASE_URL = "https://cloudaz.example.com"
SEARCH_URL = "/nextlabs-reporter/api/v1/auditLogs/search"
EXPORT_URL = "/nextlabs-reporter/api/v1/auditLogs/export"
USERS_URL = "/nextlabs-reporter/api/v1/auditLogs/users"


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


@pytest.fixture
def client_service() -> tuple[Any, AsyncEntityAuditLogService]:
    client = mock(httpx.AsyncClient)
    return client, AsyncEntityAuditLogService(client)


@pytest.mark.parametrize(
    "page_ids,total_pages",
    [
        pytest.param([12], 1, id="single-page"),
        pytest.param([1, 2], 2, id="multi-page"),
    ],
)
def test_async_search_returns_paginator(
    client_service: tuple[Any, AsyncEntityAuditLogService],
    page_ids: list[int],
    total_pages: int,
):
    client, service = client_service
    query = AuditLogQuery(start_date=100, end_date=200)

    for page_no, entry_id in enumerate(page_ids):
        entry = _make_audit_entry_data()
        entry["id"] = entry_id
        response = _make_reporter_envelope(
            content=[entry],
            total_pages=total_pages,
            total_elements=len(page_ids),
        )
        when(client).post(
            SEARCH_URL,
            json={"startDate": 100, "endDate": 200, "pageNumber": page_no},
        ).thenReturn(response)

    paginator = service.search(query)
    assert isinstance(paginator, AsyncPaginator)

    async def collect() -> list[AuditLogEntry]:
        return [entry async for entry in paginator]

    entries = asyncio.run(collect())
    assert len(entries) == len(page_ids)
    assert [entry.id for entry in entries] == page_ids


def test_async_export_returns_bytes(
    client_service: tuple[Any, AsyncEntityAuditLogService],
):
    client, service = client_service
    request_body = ExportAuditLogsRequest(ids=[5, 10])
    csv_content = b"id,timestamp,action\n5,100,LOGIN\n"
    when(client).post(
        EXPORT_URL,
        json={"ids": [5, 10]},
    ).thenReturn(httpx.Response(200, content=csv_content, request=_make_request()))

    async def run() -> bytes:
        return await service.export(request_body)

    assert asyncio.run(run()) == csv_content


def test_async_export_raises_on_error(
    client_service: tuple[Any, AsyncEntityAuditLogService],
):
    client, service = client_service
    request_body = ExportAuditLogsRequest(ids=[999])
    when(client).post(
        EXPORT_URL,
        json={"ids": [999]},
    ).thenReturn(
        httpx.Response(500, json={"message": "Export error"}, request=_make_request()),
    )

    async def run() -> bytes:
        return await service.export(request_body)

    with pytest.raises(ServerError):
        asyncio.run(run())


def test_async_list_users_returns_user_list(
    client_service: tuple[Any, AsyncEntityAuditLogService],
):
    client, service = client_service
    response = _make_data_envelope(
        data=[
            {"firstName": "Test", "lastName": "User", "username": "testuser"},
            {"firstName": "Admin", "lastName": "User", "username": "admin"},
        ],
    )
    when(client).get(USERS_URL).thenReturn(response)

    async def run() -> list[AuditLogUser]:
        return await service.list_users()

    users = asyncio.run(run())
    assert len(users) == 2
    assert users[0].username == "testuser"
