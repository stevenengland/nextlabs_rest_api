from __future__ import annotations

import asyncio
import json
from typing import TypeVar, cast

import httpx
import pytest

from nextlabs_sdk._cloudaz._component_models import ComponentNameEntry
from nextlabs_sdk._cloudaz._engine._async_runner import AsyncEndpointRunner
from nextlabs_sdk._cloudaz._engine._constructors import query_paginated
from nextlabs_sdk._pagination import AsyncPaginator
from nextlabs_sdk.exceptions import ApiError

BASE_URL = "https://cloudaz.example.com"
SPEC = query_paginated(
    ComponentNameEntry,
    "/console/api/v1/component/search/listNames/{group}",
)

T = TypeVar("T")


def _name_entry_data() -> dict[str, object]:
    return {
        "id": 101,
        "name": "Security Vulnerabilities",
        "empty": False,
        "status": "APPROVED",
    }


def _collect(paginator: AsyncPaginator[T]) -> list[T]:
    async def gather() -> list[T]:
        return [item async for item in paginator]

    return asyncio.run(gather())


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

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url=BASE_URL
    )
    runner = AsyncEndpointRunner(client)

    # when pages() is called but not iterated
    paginator = runner.pages(SPEC, {"group": "RESOURCE"})

    # then no HTTP call has happened and .total raises
    assert calls == []
    with pytest.raises(RuntimeError):
        paginator.total

    # and iterating triggers exactly the expected call
    results = _collect(paginator)
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

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url=BASE_URL
    )
    runner = AsyncEndpointRunner(client)

    paginator = runner.pages(SPEC, {"group": "RESOURCE"})
    results = _collect(paginator)

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

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url=BASE_URL
    )
    runner = AsyncEndpointRunner(client)

    paginator = runner.pages(SPEC, {"group": "RESOURCE"})
    with pytest.raises(ApiError):
        _collect(paginator)


def test_query_paginated_post_sends_fixed_json_body_and_query_params():
    # given a POST-shaped spec with a fixed body and query-string paging
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
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

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url=BASE_URL
    )
    runner = AsyncEndpointRunner(client)
    spec = query_paginated(
        ComponentNameEntry,
        "/console/api/v1/component/search/generate",
        extra_params=lambda args: {"sortBy": cast(str, args["sort_by"])},
        json_body=lambda args: args["payload"],
    )

    # when pages() is iterated
    paginator = runner.pages(spec, {"payload": {"name": "x"}, "sort_by": "rowId"})
    results = _collect(paginator)

    # then exactly one POST is issued with the fixed body and paging params
    assert len(calls) == 1
    request = calls[0]
    assert request.method == "POST"
    assert request.url.params["sortBy"] == "rowId"
    assert request.url.params["pageNo"] == "0"
    assert json.loads(request.content) == {"name": "x"}
    assert len(results) == 1


def test_malformed_entry_raises_api_error():
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

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url=BASE_URL
    )
    runner = AsyncEndpointRunner(client)

    paginator = runner.pages(SPEC, {"group": "RESOURCE"})
    # then the malformed entry is translated to ApiError, never a raw pydantic error
    with pytest.raises(ApiError):
        _collect(paginator)
