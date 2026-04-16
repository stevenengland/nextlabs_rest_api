from __future__ import annotations

import asyncio

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._component_models import (
    Component,
    Dependency,
    DeploymentResult,
)
from nextlabs_sdk._cloudaz._components import AsyncComponentService

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


def _make_component_data() -> dict[str, object]:
    return {
        "id": 101,
        "name": "Security Vulnerabilities",
        "type": "RESOURCE",
        "status": "DRAFT",
        "tags": [],
        "conditions": [],
        "memberConditions": [],
        "subComponents": [],
        "actions": [],
        "deployed": False,
        "deploymentTime": 0,
        "revisionCount": 0,
        "ownerId": 0,
        "ownerDisplayName": "Administrator",
        "createdDate": 1713171640267,
        "modifiedById": 0,
        "modifiedBy": "Administrator",
        "lastUpdatedDate": 1713171640252,
    }


def test_async_get_returns_component() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentService(client)
    response = _make_envelope(data=_make_component_data())
    when(client).get("/console/api/v1/component/mgmt/101").thenReturn(response)

    async def run() -> Component:
        return await service.get(101)

    comp = asyncio.run(run())
    assert comp.id == 101
    assert comp.name == "Security Vulnerabilities"


def test_async_get_active_returns_component() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentService(client)
    response = _make_envelope(data=_make_component_data())
    when(client).get("/console/api/v1/component/mgmt/active/101").thenReturn(response)

    async def run() -> Component:
        return await service.get_active(101)

    comp = asyncio.run(run())
    assert comp.id == 101


def test_async_create_returns_id() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentService(client)
    payload: dict[str, object] = {"name": "New", "type": "RESOURCE", "status": "DRAFT"}
    response = _make_envelope(data=101)
    when(client).post(
        "/console/api/v1/component/mgmt/add",
        json=payload,
    ).thenReturn(response)

    assert asyncio.run(service.create(payload)) == 101


def test_async_create_sub_component_returns_id() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentService(client)
    payload: dict[str, object] = {"name": "Sub", "type": "RESOURCE", "parentId": 101}
    response = _make_envelope(data=102)
    when(client).post(
        "/console/api/v1/component/mgmt/addSubComponent",
        json=payload,
    ).thenReturn(response)

    assert asyncio.run(service.create_sub_component(payload)) == 102


def test_async_modify_returns_id() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentService(client)
    payload: dict[str, object] = {"id": 101, "name": "Updated", "type": "RESOURCE"}
    response = _make_envelope(data=101)
    when(client).put(
        "/console/api/v1/component/mgmt/modify",
        json=payload,
    ).thenReturn(response)

    assert asyncio.run(service.modify(payload)) == 101


def test_async_delete_succeeds() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).delete(
        "/console/api/v1/component/mgmt/remove/101",
    ).thenReturn(response)

    asyncio.run(service.delete(101))


def test_async_bulk_delete_succeeds() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).request(
        "DELETE",
        "/console/api/v1/component/mgmt/bulkDelete",
        json=[101, 102],
    ).thenReturn(response)

    asyncio.run(service.bulk_delete([101, 102]))


def test_async_deploy_returns_results() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentService(client)
    deploy_requests: list[dict[str, object]] = [
        {"id": 101, "type": "COMPONENT", "push": True, "deploymentTime": -1},
    ]
    response_data = [
        {
            "id": 101,
            "pushResults": [
                {
                    "dpsUrl": "https://cc-prod-01:8443/dps",
                    "success": True,
                    "message": "Push Successful",
                },
            ],
        },
    ]
    response = _make_envelope(data=response_data)
    when(client).post(
        "/console/api/v1/component/mgmt/deploy",
        json=deploy_requests,
    ).thenReturn(response)

    async def run() -> list[DeploymentResult]:
        return await service.deploy(deploy_requests)

    results = asyncio.run(run())
    assert len(results) == 1
    assert results[0].push_results[0].success is True


def test_async_undeploy_succeeds() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).post(
        "/console/api/v1/component/mgmt/unDeploy",
        json=[101],
    ).thenReturn(response)

    asyncio.run(service.undeploy([101]))


def test_async_find_dependencies_returns_list() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncComponentService(client)
    dep_data = [
        {
            "id": 50,
            "type": "COMPONENT",
            "group": "RESOURCE",
            "name": "Security Vulnerabilities",
        },
    ]
    response = _make_envelope(data=dep_data)
    when(client).post(
        "/console/api/v1/component/mgmt/findDependencies",
        json=[101],
    ).thenReturn(response)

    async def run() -> list[Dependency]:
        return await service.find_dependencies([101])

    deps = asyncio.run(run())
    assert len(deps) == 1
    assert deps[0].name == "Security Vulnerabilities"
