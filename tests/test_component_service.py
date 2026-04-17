from __future__ import annotations

from typing import cast

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


def _envelope(data: object, status_code: int = 200) -> httpx.Response:
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


def _component_data() -> dict[str, object]:
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


@pytest.fixture
def ctx() -> tuple[httpx.Client, ComponentService]:
    client = cast(httpx.Client, mock(httpx.Client))
    return client, ComponentService(client)


@pytest.mark.parametrize(
    "url,method_call",
    [
        pytest.param(
            "/console/api/v1/component/mgmt/101",
            lambda svc: svc.get(101),
            id="get",
        ),
        pytest.param(
            "/console/api/v1/component/mgmt/active/101",
            lambda svc: svc.get_active(101),
            id="get-active",
        ),
    ],
)
def test_get_returns_component(ctx, url, method_call):
    client, service = ctx
    when(client).get(url).thenReturn(_envelope(data=_component_data()))

    comp = method_call(service)

    assert isinstance(comp, Component)
    assert comp.id == 101
    assert comp.name == "Security Vulnerabilities"
    assert comp.type == ComponentGroupType.RESOURCE


@pytest.mark.parametrize(
    "url,payload,response_id,method_name",
    [
        pytest.param(
            "/console/api/v1/component/mgmt/add",
            {"name": "Security Vulnerabilities", "type": "RESOURCE", "status": "DRAFT"},
            101,
            "create",
            id="create",
        ),
        pytest.param(
            "/console/api/v1/component/mgmt/addSubComponent",
            {"name": "Sub ticket", "type": "RESOURCE", "parentId": 101},
            102,
            "create_sub_component",
            id="create-sub-component",
        ),
    ],
)
def test_post_create_returns_id(ctx, url, payload, response_id, method_name):
    client, service = ctx
    when(client).post(url, json=payload).thenReturn(_envelope(data=response_id))

    assert getattr(service, method_name)(payload) == response_id


def test_modify_returns_id(ctx):
    client, service = ctx
    payload: dict[str, object] = {
        "id": 101,
        "name": "Updated Vulnerabilities",
        "type": "RESOURCE",
        "status": "DRAFT",
    }
    when(client).put(
        "/console/api/v1/component/mgmt/modify",
        json=payload,
    ).thenReturn(_envelope(data=101))

    assert service.modify(payload) == 101


def test_delete_succeeds(ctx):
    client, service = ctx
    when(client).delete(
        "/console/api/v1/component/mgmt/remove/101",
    ).thenReturn(httpx.Response(200, request=_make_request()))

    service.delete(101)


def test_bulk_delete_succeeds(ctx):
    client, service = ctx
    when(client).request(
        "DELETE",
        "/console/api/v1/component/mgmt/bulkDelete",
        json=[101, 102],
    ).thenReturn(httpx.Response(200, request=_make_request()))

    service.bulk_delete([101, 102])


def test_deploy_returns_results(ctx):
    client, service = ctx
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
    when(client).post(
        "/console/api/v1/component/mgmt/deploy",
        json=deploy_requests,
    ).thenReturn(_envelope(data=response_data))

    results = service.deploy(deploy_requests)

    assert len(results) == 1
    assert isinstance(results[0], DeploymentResult)
    assert results[0].id == 101
    assert results[0].push_results[0].success is True


def test_undeploy_succeeds(ctx):
    client, service = ctx
    when(client).post(
        "/console/api/v1/component/mgmt/unDeploy",
        json=[101, 102],
    ).thenReturn(httpx.Response(200, request=_make_request()))

    service.undeploy([101, 102])


def test_find_dependencies_returns_list(ctx):
    client, service = ctx
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
    when(client).post(
        "/console/api/v1/component/mgmt/findDependencies",
        json=[101],
    ).thenReturn(_envelope(data=dep_data))

    deps = service.find_dependencies([101])

    assert len(deps) == 1
    assert isinstance(deps[0], Dependency)
    assert deps[0].name == "Security Vulnerabilities"
    assert deps[0].provided is True


def test_get_raises_not_found(ctx):
    client, service = ctx
    when(client).get("/console/api/v1/component/mgmt/999").thenReturn(
        httpx.Response(404, json={"message": "Not found"}, request=_make_request()),
    )

    with pytest.raises(NotFoundError):
        service.get(999)
