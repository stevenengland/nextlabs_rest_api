from __future__ import annotations

import httpx
from mockito import mock, when
import pytest

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


def _tag_data(
    tag_id: int = 10,
    key: str = "dept",
    label: str = "Department",
) -> dict[str, object]:
    return {
        "id": tag_id,
        "key": key,
        "label": label,
        "type": "COMPONENT_TAG",
        "status": "ACTIVE",
    }


@pytest.fixture
def client():
    return mock(httpx.Client)


@pytest.fixture
def service(client):
    return TagService(client)


def test_list_returns_paginator(client, service):
    when(client).get(
        "/console/api/v1/config/tags/list/COMPONENT_TAG",
        params={"pageNo": 0},
    ).thenReturn(_make_envelope(data=[_tag_data()]))

    paginator = service.list(TagType.COMPONENT)

    assert isinstance(paginator, SyncPaginator)
    tags = list(paginator)
    assert len(tags) == 1
    assert isinstance(tags[0], Tag)
    assert tags[0].key == "dept"


def test_list_paginates_multiple_pages(client, service):
    page0 = _make_envelope(
        data=[_tag_data(1, "t1", "Tag1")],
        total_pages=2,
        total_records=2,
    )
    page1 = _make_envelope(
        data=[_tag_data(2, "t2", "Tag2")],
        page_no=1,
        total_pages=2,
        total_records=2,
    )

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


def test_get_returns_single_tag(client, service):
    when(client).get("/console/api/v1/config/tags/10").thenReturn(
        _make_envelope(data=_tag_data()),
    )

    tag = service.get(10)

    assert isinstance(tag, Tag)
    assert tag.id == 10
    assert tag.key == "dept"


def test_create_returns_id(client, service):
    when(client).post(
        "/console/api/v1/config/tags/add/COMPONENT_TAG",
        json={
            "key": "env",
            "label": "Environment",
            "type": "COMPONENT_TAG",
            "status": "ACTIVE",
        },
    ).thenReturn(_make_envelope(data=42))

    assert service.create(TagType.COMPONENT, key="env", label="Environment") == 42


def test_delete_succeeds(client, service):
    when(client).delete("/console/api/v1/config/tags/remove/10").thenReturn(
        httpx.Response(200, request=_make_request()),
    )

    service.delete(10)


def test_get_raises_not_found(client, service):
    when(client).get("/console/api/v1/config/tags/999").thenReturn(
        httpx.Response(404, json={"message": "Not found"}, request=_make_request()),
    )

    with pytest.raises(NotFoundError):
        service.get(999)


def test_list_sends_page_size_and_show_hidden(client, service):
    when(client).get(
        "/console/api/v1/config/tags/list/COMPONENT_TAG",
        params={"pageNo": 0, "pageSize": 50, "showHidden": "true"},
    ).thenReturn(_make_envelope(data=[_tag_data()], page_size=50))

    tags = list(service.list(TagType.COMPONENT, page_size=50, show_hidden=True))

    assert len(tags) == 1


def test_list_show_hidden_false_is_sent_as_string(client, service):
    when(client).get(
        "/console/api/v1/config/tags/list/COMPONENT_TAG",
        params={"pageNo": 0, "showHidden": "false"},
    ).thenReturn(_make_envelope(data=[]))

    list(service.list(TagType.COMPONENT, show_hidden=False))


def test_first_page_reports_server_page_size(client, service):
    when(client).get(
        "/console/api/v1/config/tags/list/COMPONENT_TAG",
        params={"pageNo": 0, "pageSize": 25},
    ).thenReturn(_make_envelope(data=[_tag_data()], page_size=25))

    page = service.list(TagType.COMPONENT, page_size=25).first_page()

    assert page.page_size == 25
