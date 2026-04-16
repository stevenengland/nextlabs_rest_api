from __future__ import annotations

import asyncio

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._component_type_models import (
    AttributeConfig,
    ComponentType,
)
from nextlabs_sdk._cloudaz._component_types import AsyncComponentTypeService

BASE_URL = "https://cloudaz.example.com"


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_envelope(
    data: object,
    status_code: int = 200,
) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": data,
            "pageNo": 0,
            "pageSize": 10,
            "totalPages": 1,
            "totalNoOfRecords": 1,
            "additionalAttributes": None,
        },
        request=_make_request(),
    )


def _make_component_type_data() -> dict[str, object]:
    return {
        "id": 42,
        "name": "Support Tickets",
        "shortName": "support_tickets",
        "type": "RESOURCE",
        "status": "ACTIVE",
        "tags": [],
        "attributes": [],
        "actions": [],
        "obligations": [],
        "version": 1,
        "ownerId": 0,
        "ownerDisplayName": "Administrator",
        "createdDate": 1713171640267,
        "lastUpdatedDate": 1713171640252,
        "modifiedById": 0,
        "modifiedBy": "Administrator",
    }


def test_async_get_returns_component_type() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentTypeService(client)
    response = _make_envelope(data=_make_component_type_data())
    when(client).get("/console/api/v1/policyModel/mgmt/42").thenReturn(response)

    async def run() -> ComponentType:
        return await service.get(42)

    ct = asyncio.run(run())
    assert ct.id == 42
    assert ct.name == "Support Tickets"


def test_async_get_active_returns_component_type() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentTypeService(client)
    response = _make_envelope(data=_make_component_type_data())
    when(client).get("/console/api/v1/policyModel/mgmt/active/42").thenReturn(response)

    async def run() -> ComponentType:
        return await service.get_active(42)

    ct = asyncio.run(run())
    assert ct.id == 42


def test_async_create_returns_id() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentTypeService(client)
    payload: dict[str, object] = {
        "name": "New",
        "shortName": "new",
        "type": "RESOURCE",
        "status": "ACTIVE",
    }
    response = _make_envelope(data=99)
    when(client).post(
        "/console/api/v1/policyModel/mgmt/add",
        json=payload,
    ).thenReturn(response)

    async def run() -> int:
        return await service.create(payload)

    assert asyncio.run(run()) == 99


def test_async_modify_returns_id() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentTypeService(client)
    payload: dict[str, object] = {
        "id": 42,
        "name": "Updated",
        "shortName": "updated",
        "type": "RESOURCE",
        "status": "ACTIVE",
        "version": 1,
    }
    response = _make_envelope(data=42)
    when(client).put(
        "/console/api/v1/policyModel/mgmt/modify",
        json=payload,
    ).thenReturn(response)

    async def run() -> int:
        return await service.modify(payload)

    assert asyncio.run(run()) == 42


def test_async_delete_succeeds() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentTypeService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).delete(
        "/console/api/v1/policyModel/mgmt/remove/42",
    ).thenReturn(response)

    asyncio.run(service.delete(42))


def test_async_bulk_delete_succeeds() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentTypeService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).request(
        "DELETE",
        "/console/api/v1/policyModel/mgmt/bulkDelete",
        json=[1, 2],
    ).thenReturn(response)

    asyncio.run(service.bulk_delete([1, 2]))


def test_async_clone_returns_id() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentTypeService(client)
    response = _make_envelope(data=100)
    when(client).post(
        "/console/api/v1/policyModel/mgmt/clone",
        json=42,
    ).thenReturn(response)

    async def run() -> int:
        return await service.clone(42)

    assert asyncio.run(run()) == 100


def test_async_list_extra_subject_attributes() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentTypeService(client)
    attr_data = [
        {
            "name": "SID",
            "shortName": "sid",
            "dataType": "STRING",
            "operatorConfigs": [],
            "sortOrder": 0,
        },
    ]
    response = _make_envelope(data=attr_data)
    when(client).get(
        "/console/api/v1/policyModel/mgmt/extraSubjectAttribs/USER",
    ).thenReturn(response)

    async def run() -> list[AttributeConfig]:
        return await service.list_extra_subject_attributes("USER")

    attrs = asyncio.run(run())
    assert len(attrs) == 1
    assert attrs[0].short_name == "sid"
