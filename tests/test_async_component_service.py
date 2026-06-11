from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, TypeVar, cast

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk.cloudaz import (
    AsyncComponentService,
    Component,
    ComponentHistoryEntry,
    ComponentRevision,
)
from nextlabs_sdk._cloudaz._component_models import Dependency, DeploymentResult
from nextlabs_sdk.exceptions import ApiError, NotFoundError

BASE_URL = "https://cloudaz.example.com"
MGMT = "/console/api/v1/component/mgmt"

T = TypeVar("T")


def _run(coro: Awaitable[T]) -> T:
    return asyncio.run(coro)  # type: ignore[arg-type]


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


def _paginated_envelope(
    data: object,
    page_size: int = 10,
    total_pages: int = 1,
    total_records: int = 1,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": data,
            "pageNo": 1,
            "pageSize": page_size,
            "totalPages": total_pages,
            "totalNoOfRecords": total_records,
            "additionalAttributes": None,
        },
        request=_make_request(),
    )


def _history_entry_data() -> dict[str, object]:
    return {
        "id": 770,
        "revision": "3",
        "name": "ROOT_101/pentest_component",
        "description": None,
        "activeFrom": 1761133292235,
        "activeTo": 1761133292235,
        "componentDetail": None,
        "createdDate": 1761133292266,
        "createdBy": "me",
        "modifiedBy": "me",
        "lastUpdatedDate": 1761133292250,
        "submittedBy": "me",
        "submittedDate": 1761133292266,
        "actionType": "UN",
    }


def _revision_data() -> dict[str, object]:
    return {
        **_history_entry_data(),
        "id": 555,
        "revision": "1",
        "componentDetail": _component_data(),
    }


@pytest.fixture
def ctx() -> tuple[httpx.AsyncClient, AsyncComponentService]:
    client = cast(httpx.AsyncClient, mock(httpx.AsyncClient))
    return client, AsyncComponentService(client)


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
def test_async_get_returns_component(
    ctx,
    url: str,
    method_call: Callable[[AsyncComponentService], Awaitable[Component]],
):
    client, service = ctx
    when(client).get(url).thenReturn(_envelope(data=_component_data()))

    comp = _run(method_call(service))
    assert comp.id == 101
    assert comp.name == "Security Vulnerabilities"


@pytest.mark.parametrize(
    "url,payload,response_id,method_name",
    [
        pytest.param(
            "/console/api/v1/component/mgmt/add",
            {"name": "New", "type": "RESOURCE", "status": "DRAFT"},
            101,
            "create",
            id="create",
        ),
        pytest.param(
            "/console/api/v1/component/mgmt/addSubComponent",
            {"name": "Sub", "type": "RESOURCE", "parentId": 101},
            102,
            "create_sub_component",
            id="create-sub-component",
        ),
    ],
)
def test_async_create_returns_id(ctx, url, payload, response_id, method_name):
    client, service = ctx
    when(client).post(url, json=payload).thenReturn(_envelope(data=response_id))

    assert _run(getattr(service, method_name)(payload)) == response_id


def test_async_modify_returns_id(ctx):
    client, service = ctx
    payload: dict[str, object] = {"id": 101, "name": "Updated", "type": "RESOURCE"}
    when(client).put(
        "/console/api/v1/component/mgmt/modify",
        json=payload,
    ).thenReturn(_envelope(data=101))

    assert _run(service.modify(payload)) == 101


def test_async_delete_succeeds(ctx):
    client, service = ctx
    when(client).delete(
        "/console/api/v1/component/mgmt/remove/101",
    ).thenReturn(httpx.Response(200, request=_make_request()))

    _run(service.delete(101))


def test_async_bulk_delete_succeeds(ctx):
    client, service = ctx
    when(client).request(
        "DELETE",
        "/console/api/v1/component/mgmt/bulkDelete",
        json=[101, 102],
    ).thenReturn(httpx.Response(200, request=_make_request()))

    _run(service.bulk_delete([101, 102]))


def test_async_deploy_returns_results(ctx):
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

    results: list[DeploymentResult] = _run(service.deploy(deploy_requests))
    assert len(results) == 1
    assert results[0].push_results[0].success is True


def test_async_undeploy_succeeds(ctx):
    client, service = ctx
    when(client).post(
        "/console/api/v1/component/mgmt/unDeploy",
        json=[101],
    ).thenReturn(httpx.Response(200, request=_make_request()))

    _run(service.undeploy([101]))


def test_async_find_dependencies_returns_list(ctx):
    client, service = ctx
    dep_data = [
        {
            "id": 50,
            "type": "COMPONENT",
            "group": "RESOURCE",
            "name": "Security Vulnerabilities",
        },
    ]
    when(client).post(
        "/console/api/v1/component/mgmt/findDependencies",
        json=[101],
    ).thenReturn(_envelope(data=dep_data))

    deps: list[Dependency] = _run(service.find_dependencies([101]))
    assert len(deps) == 1
    assert deps[0].name == "Security Vulnerabilities"


def test_async_list_history_returns_all_entries(ctx):
    client, service = ctx
    e1 = _history_entry_data()
    e2 = {**_history_entry_data(), "id": 769, "revision": "2", "actionType": "DE"}
    e3 = {**_history_entry_data(), "id": 768, "revision": "1", "actionType": "DE"}
    when(client).get(f"{MGMT}/history/42").thenReturn(
        _paginated_envelope([e1, e2, e3], page_size=3, total_pages=3, total_records=3),
    )

    results = _run(service.list_history(42))

    assert [entry.revision for entry in results] == [3, 2, 1]
    assert isinstance(results[0], ComponentHistoryEntry)
    assert results[0].action_type == "UN"


def test_async_list_history_raises_when_records_exceed_returned(ctx):
    client, service = ctx
    when(client).get(f"{MGMT}/history/42").thenReturn(
        _paginated_envelope(
            [_history_entry_data()], page_size=1, total_pages=180, total_records=180
        ),
    )
    with pytest.raises(ApiError):
        _run(service.list_history(42))


def test_async_list_history_raises_not_found(ctx):
    client, service = ctx
    when(client).get(f"{MGMT}/history/999").thenReturn(
        httpx.Response(404, json={"message": "Not found"}, request=_make_request()),
    )
    with pytest.raises(NotFoundError):
        _run(service.list_history(999))


def test_async_get_revision_returns_component_revision(ctx):
    client, service = ctx
    when(client).get(f"{MGMT}/viewRevision/555/1").thenReturn(
        _envelope(_revision_data())
    )

    rev = _run(service.get_revision(555, 1))

    assert isinstance(rev, ComponentRevision)
    assert rev.revision == 1
    assert isinstance(rev.component_detail, Component)
    assert rev.component_detail.id == _component_data()["id"]


def test_async_get_revision_raises_not_found(ctx):
    client, service = ctx
    when(client).get(f"{MGMT}/viewRevision/999/1").thenReturn(
        httpx.Response(404, json={"message": "Not found"}, request=_make_request()),
    )
    with pytest.raises(NotFoundError):
        _run(service.get_revision(999, 1))
