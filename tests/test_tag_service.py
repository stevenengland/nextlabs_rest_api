from __future__ import annotations

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._models import Tag, TagType
from nextlabs_sdk._cloudaz._tags import TagService
from nextlabs_sdk._pagination import SyncPaginator
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


def _make_tag_data() -> dict[str, object]:
    return {
        "id": 10,
        "key": "dept",
        "label": "Department",
        "type": "COMPONENT_TAG",
        "status": "ACTIVE",
    }


def test_list_returns_paginator() -> None:
    client = mock(httpx.Client)
    service = TagService(client)
    response = _make_envelope(
        data=[_make_tag_data()],
        total_pages=1,
        total_records=1,
    )
    when(client).get(
        "/console/api/v1/config/tags/list/COMPONENT_TAG",
        params={"pageNo": 0},
    ).thenReturn(response)

    paginator = service.list(TagType.COMPONENT)

    assert isinstance(paginator, SyncPaginator)
    tags = list(paginator)
    assert len(tags) == 1
    assert isinstance(tags[0], Tag)
    assert tags[0].key == "dept"


def test_list_paginates_multiple_pages() -> None:
    client = mock(httpx.Client)
    service = TagService(client)
    tag1 = {
        "id": 1,
        "key": "t1",
        "label": "Tag1",
        "type": "COMPONENT_TAG",
        "status": "ACTIVE",
    }
    tag2 = {
        "id": 2,
        "key": "t2",
        "label": "Tag2",
        "type": "COMPONENT_TAG",
        "status": "ACTIVE",
    }

    page0 = _make_envelope(data=[tag1], total_pages=2, total_records=2)
    page1 = _make_envelope(data=[tag2], page_no=1, total_pages=2, total_records=2)

    when(client).get(
        "/console/api/v1/config/tags/list/COMPONENT_TAG",
        params={"pageNo": 0},
    ).thenReturn(page0)
    when(client).get(
        "/console/api/v1/config/tags/list/COMPONENT_TAG",
        params={"pageNo": 1},
    ).thenReturn(page1)

    tags = list(service.list(TagType.COMPONENT))

    assert len(tags) == 2
    assert tags[0].key == "t1"
    assert tags[1].key == "t2"


def test_get_returns_single_tag() -> None:
    client = mock(httpx.Client)
    service = TagService(client)
    response = _make_envelope(data=_make_tag_data())
    when(client).get("/console/api/v1/config/tags/10").thenReturn(response)

    tag = service.get(10)

    assert isinstance(tag, Tag)
    assert tag.id == 10
    assert tag.key == "dept"


def test_create_returns_id() -> None:
    client = mock(httpx.Client)
    service = TagService(client)
    response = _make_envelope(data=42)
    when(client).post(
        "/console/api/v1/config/tags/add/COMPONENT_TAG",
        json={
            "key": "env",
            "label": "Environment",
            "type": "COMPONENT_TAG",
            "status": "ACTIVE",
        },
    ).thenReturn(response)

    tag_id = service.create(TagType.COMPONENT, key="env", label="Environment")

    assert tag_id == 42


def test_delete_succeeds() -> None:
    client = mock(httpx.Client)
    service = TagService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).delete("/console/api/v1/config/tags/remove/10").thenReturn(response)

    service.delete(10)


def test_get_raises_not_found() -> None:
    client = mock(httpx.Client)
    service = TagService(client)
    response = httpx.Response(
        404,
        json={"message": "Not found"},
        request=_make_request(),
    )
    when(client).get("/console/api/v1/config/tags/999").thenReturn(response)

    with pytest.raises(NotFoundError):
        service.get(999)
