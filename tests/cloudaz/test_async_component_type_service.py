from __future__ import annotations

import asyncio
from typing import Any, Coroutine, TypeVar

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._component_type_models import (
    AttributeConfig,
    ComponentType,
)
from nextlabs_sdk._cloudaz._component_types import AsyncComponentTypeService

T = TypeVar("T")

BASE_URL = "https://cloudaz.example.com"


def _run_async(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_envelope(data, status_code: int = 200) -> httpx.Response:
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


@pytest.fixture
def service_client():
    client = mock(httpx.AsyncClient)
    return AsyncComponentTypeService(client), client


@pytest.mark.parametrize(
    "method,path",
    [
        pytest.param("get", "/console/api/v1/policyModel/mgmt/42", id="get"),
        pytest.param(
            "get_active", "/console/api/v1/policyModel/mgmt/active/42", id="get-active"
        ),
    ],
)
def test_async_get_returns_component_type(service_client, method, path):
    service, client = service_client
    when(client).get(path).thenReturn(_make_envelope(data=_make_component_type_data()))

    ct = _run_async(getattr(service, method)(42))

    assert isinstance(ct, ComponentType)
    assert ct.id == 42
    assert ct.name == "Support Tickets"


def test_async_create_returns_id(service_client):
    service, client = service_client
    payload = {
        "name": "New",
        "shortName": "new",
        "type": "RESOURCE",
        "status": "ACTIVE",
    }
    when(client).post(
        "/console/api/v1/policyModel/mgmt/add",
        json=payload,
    ).thenReturn(_make_envelope(data=99))

    assert _run_async(service.create(payload)) == 99


def test_async_modify_returns_id(service_client):
    service, client = service_client
    payload = {
        "id": 42,
        "name": "Updated",
        "shortName": "updated",
        "type": "RESOURCE",
        "status": "ACTIVE",
        "version": 1,
    }
    when(client).put(
        "/console/api/v1/policyModel/mgmt/modify",
        json=payload,
    ).thenReturn(_make_envelope(data=42))

    assert _run_async(service.modify(payload)) == 42


def test_async_delete_succeeds(service_client):
    service, client = service_client
    when(client).delete("/console/api/v1/policyModel/mgmt/remove/42").thenReturn(
        httpx.Response(200, request=_make_request()),
    )

    _run_async(service.delete(42))


def test_async_bulk_delete_succeeds(service_client):
    service, client = service_client
    when(client).request(
        "DELETE",
        "/console/api/v1/policyModel/mgmt/bulkDelete",
        json=[1, 2],
    ).thenReturn(httpx.Response(200, request=_make_request()))

    _run_async(service.bulk_delete([1, 2]))


def test_async_clone_returns_id(service_client):
    service, client = service_client
    when(client).post(
        "/console/api/v1/policyModel/mgmt/clone",
        json=42,
    ).thenReturn(_make_envelope(data=100))

    assert _run_async(service.clone(42)) == 100


def test_async_list_extra_subject_attributes(service_client):
    service, client = service_client
    attr_data = [
        {
            "name": "SID",
            "shortName": "sid",
            "dataType": "STRING",
            "operatorConfigs": [],
            "sortOrder": 0,
        },
    ]
    when(client).get(
        "/console/api/v1/policyModel/mgmt/extraSubjectAttribs/USER",
    ).thenReturn(_make_envelope(data=attr_data))

    attrs: list[AttributeConfig] = _run_async(
        service.list_extra_subject_attributes("USER")
    )

    assert len(attrs) == 1
    assert attrs[0].short_name == "sid"
