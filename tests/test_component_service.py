from __future__ import annotations

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._component_models import (
    Component,
    ComponentGroupType,
    Dependency,
    DeploymentResult,
)
from nextlabs_sdk._cloudaz._components import ComponentService
from nextlabs_sdk.exceptions import NotFoundError

BASE_URL = "https://cloudaz.example.com"


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_envelope(
    data: object,
    status_code: int = 200,
    page_no: int = 0,
    page_size: int = 10,
    total_pages: int = 1,
    total_records: int = 1,
) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": data,
            "pageNo": page_no,
            "pageSize": page_size,
            "totalPages": total_pages,
            "totalNoOfRecords": total_records,
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


def test_get_returns_component() -> None:
    client = mock(httpx.Client)
    service = ComponentService(client)
    response = _make_envelope(data=_make_component_data())
    when(client).get("/console/api/v1/component/mgmt/101").thenReturn(response)

    comp = service.get(101)

    assert isinstance(comp, Component)
    assert comp.id == 101
    assert comp.name == "Security Vulnerabilities"
    assert comp.type == ComponentGroupType.RESOURCE


def test_get_active_returns_component() -> None:
    client = mock(httpx.Client)
    service = ComponentService(client)
    response = _make_envelope(data=_make_component_data())
    when(client).get("/console/api/v1/component/mgmt/active/101").thenReturn(response)

    comp = service.get_active(101)

    assert isinstance(comp, Component)
    assert comp.id == 101


def test_create_returns_id() -> None:
    client = mock(httpx.Client)
    service = ComponentService(client)
    payload: dict[str, object] = {
        "name": "Security Vulnerabilities",
        "type": "RESOURCE",
        "status": "DRAFT",
    }
    response = _make_envelope(data=101)
    when(client).post(
        "/console/api/v1/component/mgmt/add",
        json=payload,
    ).thenReturn(response)

    result = service.create(payload)

    assert result == 101


def test_create_sub_component_returns_id() -> None:
    client = mock(httpx.Client)
    service = ComponentService(client)
    payload: dict[str, object] = {
        "name": "Sub ticket",
        "type": "RESOURCE",
        "parentId": 101,
    }
    response = _make_envelope(data=102)
    when(client).post(
        "/console/api/v1/component/mgmt/addSubComponent",
        json=payload,
    ).thenReturn(response)

    result = service.create_sub_component(payload)

    assert result == 102


def test_modify_returns_id() -> None:
    client = mock(httpx.Client)
    service = ComponentService(client)
    payload: dict[str, object] = {
        "id": 101,
        "name": "Updated Vulnerabilities",
        "type": "RESOURCE",
        "status": "DRAFT",
    }
    response = _make_envelope(data=101)
    when(client).put(
        "/console/api/v1/component/mgmt/modify",
        json=payload,
    ).thenReturn(response)

    result = service.modify(payload)

    assert result == 101


def test_delete_succeeds() -> None:
    client = mock(httpx.Client)
    service = ComponentService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).delete(
        "/console/api/v1/component/mgmt/remove/101",
    ).thenReturn(response)

    service.delete(101)


def test_bulk_delete_succeeds() -> None:
    client = mock(httpx.Client)
    service = ComponentService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).request(
        "DELETE",
        "/console/api/v1/component/mgmt/bulkDelete",
        json=[101, 102],
    ).thenReturn(response)

    service.bulk_delete([101, 102])


def test_deploy_returns_results() -> None:
    client = mock(httpx.Client)
    service = ComponentService(client)
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

    results = service.deploy(deploy_requests)

    assert len(results) == 1
    assert isinstance(results[0], DeploymentResult)
    assert results[0].id == 101
    assert results[0].push_results[0].success is True


def test_undeploy_succeeds() -> None:
    client = mock(httpx.Client)
    service = ComponentService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).post(
        "/console/api/v1/component/mgmt/unDeploy",
        json=[101, 102],
    ).thenReturn(response)

    service.undeploy([101, 102])


def test_find_dependencies_returns_list() -> None:
    client = mock(httpx.Client)
    service = ComponentService(client)
    dep_data = [
        {
            "id": 50,
            "type": "COMPONENT",
            "group": "RESOURCE",
            "name": "Security Vulnerabilities",
            "folderPath": None,
            "optional": False,
            "provided": True,
            "sub": False,
        },
    ]
    response = _make_envelope(data=dep_data)
    when(client).post(
        "/console/api/v1/component/mgmt/findDependencies",
        json=[101],
    ).thenReturn(response)

    deps = service.find_dependencies([101])

    assert len(deps) == 1
    assert isinstance(deps[0], Dependency)
    assert deps[0].name == "Security Vulnerabilities"
    assert deps[0].provided is True


def test_get_raises_not_found() -> None:
    client = mock(httpx.Client)
    service = ComponentService(client)
    response = httpx.Response(
        404,
        json={"message": "Not found"},
        request=_make_request(),
    )
    when(client).get("/console/api/v1/component/mgmt/999").thenReturn(response)

    with pytest.raises(NotFoundError):
        service.get(999)
