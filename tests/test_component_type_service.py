from __future__ import annotations

import httpx
import pytest
from mockito import mock, when

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


def test_get_returns_component_type() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeService(client)
    response = _make_envelope(data=_make_component_type_data())
    when(client).get("/console/api/v1/policyModel/mgmt/42").thenReturn(response)

    ct = service.get(42)

    assert isinstance(ct, ComponentType)
    assert ct.id == 42
    assert ct.name == "Support Tickets"
    assert ct.type == ComponentTypeType.RESOURCE
    assert len(ct.attributes) == 1
    assert ct.attributes[0].name == "Priority"


def test_get_active_returns_component_type() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeService(client)
    response = _make_envelope(data=_make_component_type_data())
    when(client).get("/console/api/v1/policyModel/mgmt/active/42").thenReturn(response)

    ct = service.get_active(42)

    assert isinstance(ct, ComponentType)
    assert ct.id == 42


def test_create_returns_id() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeService(client)
    payload: dict[str, object] = {
        "name": "Support Tickets",
        "shortName": "support_tickets",
        "type": "RESOURCE",
        "status": "ACTIVE",
    }
    response = _make_envelope(data=99)
    when(client).post(
        "/console/api/v1/policyModel/mgmt/add",
        json=payload,
    ).thenReturn(response)

    result = service.create(payload)

    assert result == 99


def test_modify_returns_id() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeService(client)
    payload: dict[str, object] = {
        "id": 42,
        "name": "Support Tickets Updated",
        "shortName": "support_tickets",
        "type": "RESOURCE",
        "status": "ACTIVE",
        "version": 1,
    }
    response = _make_envelope(data=42)
    when(client).put(
        "/console/api/v1/policyModel/mgmt/modify",
        json=payload,
    ).thenReturn(response)

    result = service.modify(payload)

    assert result == 42


def test_delete_succeeds() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).delete(
        "/console/api/v1/policyModel/mgmt/remove/42",
    ).thenReturn(response)

    service.delete(42)


def test_bulk_delete_succeeds() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).request(
        "DELETE",
        "/console/api/v1/policyModel/mgmt/bulkDelete",
        json=[1, 2, 3],
    ).thenReturn(response)

    service.bulk_delete([1, 2, 3])


def test_clone_returns_id() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeService(client)
    response = _make_envelope(data=100)
    when(client).post(
        "/console/api/v1/policyModel/mgmt/clone",
        json=42,
    ).thenReturn(response)

    result = service.clone(42)

    assert result == 100


def test_list_extra_subject_attributes_returns_list() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeService(client)
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
    response = _make_envelope(data=attr_data)
    when(client).get(
        "/console/api/v1/policyModel/mgmt/extraSubjectAttribs/USER",
    ).thenReturn(response)

    attrs = service.list_extra_subject_attributes("USER")

    assert len(attrs) == 1
    assert isinstance(attrs[0], AttributeConfig)
    assert attrs[0].short_name == "windowsSid"
    assert attrs[0].data_type == AttributeDataType.STRING


def test_get_raises_not_found() -> None:
    client = mock(httpx.Client)
    service = ComponentTypeService(client)
    response = httpx.Response(
        404,
        json={"message": "Not found"},
        request=_make_request(),
    )
    when(client).get("/console/api/v1/policyModel/mgmt/999").thenReturn(response)

    with pytest.raises(NotFoundError):
        service.get(999)
