from __future__ import annotations

import httpx
import pytest

from nextlabs_sdk._cloudaz._component_models import ComponentNameEntry
from nextlabs_sdk._cloudaz._engine._constructors import query_paginated
from nextlabs_sdk._cloudaz._engine._runner import SyncEndpointRunner
from nextlabs_sdk.exceptions import ApiError

BASE_URL = "https://cloudaz.example.com"
SPEC = query_paginated(
    ComponentNameEntry,
    "/console/api/v1/component/search/listNames/{group}",
)


def _name_entry_data() -> dict[str, object]:
    return {
        "id": 101,
        "name": "Security Vulnerabilities",
        "empty": False,
        "status": "APPROVED",
    }


def test_pages_defers_first_http_call_until_iteration():
    # given a runner over a MockTransport counting requests
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "statusCode": "1004",
                "message": "ok",
                "data": [_name_entry_data()],
                "pageSize": 1,
                "totalPages": 1,
                "totalNoOfRecords": 1,
            },
            request=request,
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url=BASE_URL)
    runner = SyncEndpointRunner(client)

    # when pages() is called but not iterated
    paginator = runner.pages(SPEC, {"group": "RESOURCE"})

    # then no HTTP call has happened and .total raises
    assert calls == []
    with pytest.raises(RuntimeError):
        paginator.total

    # and iterating triggers exactly the expected call
    results = list(paginator)
    assert calls == ["/console/api/v1/component/search/listNames/RESOURCE"]
    assert len(results) == 1
    assert paginator.total == 1


def test_no_data_yields_empty_terminal_page():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "statusCode": "5000",
                "message": "No data found",
                "data": [],
            },
            request=request,
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url=BASE_URL)
    runner = SyncEndpointRunner(client)

    paginator = runner.pages(SPEC, {"group": "RESOURCE"})
    results = list(paginator)

    assert results == []
    assert len(calls) == 1


def test_envelope_error_raises_api_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "statusCode": "9001",
                "message": "boom",
            },
            request=request,
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url=BASE_URL)
    runner = SyncEndpointRunner(client)

    paginator = runner.pages(SPEC, {"group": "RESOURCE"})
    with pytest.raises(ApiError):
        list(paginator)


def test_malformed_entry_raises_next_labs_error():
    # given a page entry that fails model validation
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "statusCode": "1004",
                "message": "ok",
                "data": [{"id": "not-an-int"}],
                "pageSize": 1,
                "totalPages": 1,
                "totalNoOfRecords": 1,
            },
            request=request,
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url=BASE_URL)
    runner = SyncEndpointRunner(client)

    paginator = runner.pages(SPEC, {"group": "RESOURCE"})
    # then the malformed entry is translated to ApiError, never a raw pydantic error
    with pytest.raises(ApiError):
        list(paginator)
