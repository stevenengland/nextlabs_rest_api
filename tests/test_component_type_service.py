from __future__ import annotations

import httpx
from mockito import mock, when
import pytest

from nextlabs_sdk._cloudaz._component_type_models import (
    AttributeConfig,
    AttributeDataType,
    ComponentType,
    ComponentTypeType,
)
from nextlabs_sdk._cloudaz._component_types import ComponentTypeService
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


def _make_component_type_data() -> dict[str, object]:
    return {
        "id": 42,
        "name": "Support Tickets",
        "shortName": "support_tickets",
        "description": "Support Tickets Description",
        "type": "RESOURCE",
        "status": "ACTIVE",
        "tags": [],
        "attributes": [
            {
                "id": 16,
                "name": "Priority",
                "shortName": "priority",
                "dataType": "NUMBER",
                "operatorConfigs": [
                    {"id": 1, "key": "=", "label": "=", "dataType": "NUMBER"},
                ],
                "regExPattern": None,
                "sortOrder": 0,
            },
        ],
        "actions": [
            {"id": 81, "name": "View", "shortName": "VIEW_TKTS", "sortOrder": 0},
        ],
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
def client():
    return mock(httpx.Client)


@pytest.fixture
def service(client):
    return ComponentTypeService(client)


@pytest.mark.parametrize(
    "method,url",
    [
        pytest.param("get", "/console/api/v1/policyModel/mgmt/42", id="get"),
        pytest.param(
            "get_active",
            "/console/api/v1/policyModel/mgmt/active/42",
            id="get-active",
        ),
    ],
)
def test_get_variants_return_component_type(client, service, method, url):
    when(client).get(url).thenReturn(_make_envelope(data=_make_component_type_data()))

    ct = getattr(service, method)(42)

    assert isinstance(ct, ComponentType)
    assert ct.id == 42
    if method == "get":
        assert ct.name == "Support Tickets"
        assert ct.type == ComponentTypeType.RESOURCE
        assert len(ct.attributes) == 1
        assert ct.attributes[0].name == "Priority"


def test_create_returns_id(client, service):
    payload: dict[str, object] = {
        "name": "Support Tickets",
        "shortName": "support_tickets",
        "type": "RESOURCE",
        "status": "ACTIVE",
    }
    when(client).post(
        "/console/api/v1/policyModel/mgmt/add",
        json=payload,
    ).thenReturn(_make_envelope(data=99))

    assert service.create(payload) == 99


def test_modify_returns_id(client, service):
    payload: dict[str, object] = {
        "id": 42,
        "name": "Support Tickets Updated",
        "shortName": "support_tickets",
        "type": "RESOURCE",
        "status": "ACTIVE",
        "version": 1,
    }
    when(client).put(
        "/console/api/v1/policyModel/mgmt/modify",
        json=payload,
    ).thenReturn(_make_envelope(data=42))

    assert service.modify(payload) == 42


def test_delete_succeeds(client, service):
    when(client).delete(
        "/console/api/v1/policyModel/mgmt/remove/42",
    ).thenReturn(httpx.Response(200, request=_make_request()))

    service.delete(42)


def test_bulk_delete_succeeds(client, service):
    when(client).request(
        "DELETE",
        "/console/api/v1/policyModel/mgmt/bulkDelete",
        json=[1, 2, 3],
    ).thenReturn(httpx.Response(200, request=_make_request()))

    service.bulk_delete([1, 2, 3])


def test_clone_returns_id(client, service):
    when(client).post(
        "/console/api/v1/policyModel/mgmt/clone",
        json=42,
    ).thenReturn(_make_envelope(data=100))

    assert service.clone(42) == 100


def test_list_extra_subject_attributes_returns_list(client, service):
    attr_data = [
        {
            "name": "Windows User SID",
            "shortName": "windowsSid",
            "dataType": "STRING",
            "operatorConfigs": [
                {"id": 5, "key": "!=", "label": "is not", "dataType": "STRING"},
            ],
            "sortOrder": 0,
        },
    ]
    when(client).get(
        "/console/api/v1/policyModel/mgmt/extraSubjectAttribs/USER",
    ).thenReturn(_make_envelope(data=attr_data))

    attrs = service.list_extra_subject_attributes("USER")

    assert len(attrs) == 1
    assert isinstance(attrs[0], AttributeConfig)
    assert attrs[0].short_name == "windowsSid"
    assert attrs[0].data_type == AttributeDataType.STRING


def test_get_raises_not_found(client, service):
    when(client).get("/console/api/v1/policyModel/mgmt/999").thenReturn(
        httpx.Response(404, json={"message": "Not found"}, request=_make_request()),
    )

    with pytest.raises(NotFoundError):
        service.get(999)
