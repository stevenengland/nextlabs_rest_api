from __future__ import annotations

import asyncio
from typing import Callable

import httpx
import pytest

from pydantic import BaseModel

from nextlabs_sdk._cloudaz._response import (
    build_page,
    parse_data,
    parse_pageable,
    parse_paginated,
    parse_raw,
    parse_reporter_paginated,
)
from nextlabs_sdk._pagination import AsyncPaginator, PageResult, SyncPaginator
from nextlabs_sdk.exceptions import ApiError, NotFoundError, ServerError


def _make_request() -> httpx.Request:
    return httpx.Request("GET", "https://test/api")


def _no_data_envelope(status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={"statusCode": "5000", "message": "No data found"},
        request=_make_request(),
    )


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


def _err_response(status_code: int, message: str) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={"message": message},
        request=_make_request(),
    )


def _non_json_response(status_code: int = 200, content: bytes = b"x") -> httpx.Response:
    return httpx.Response(status_code, content=content, request=_make_request())


@pytest.mark.parametrize(
    "data,expected",
    [
        pytest.param({"id": 1, "name": "test"}, {"id": 1, "name": "test"}, id="dict"),
        pytest.param([{"id": 1}, {"id": 2}], [{"id": 1}, {"id": 2}], id="list"),
    ],
)
def test_parse_data_extracts_data_field(data, expected):
    assert parse_data(_make_envelope(data=data)) == expected


def test_parse_paginated_extracts_all_fields():
    response = _make_envelope(
        data=[{"id": 1}],
        total_pages=5,
        total_records=42,
        page_size=25,
    )
    data, total_pages, total_records, page_size = parse_paginated(response)
    assert data == [{"id": 1}]
    assert total_pages == 5
    assert total_records == 42
    assert page_size == 25


def test_parse_paginated_page_size_missing_returns_none():
    response = httpx.Response(
        200,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": [{"id": 1}],
            "totalPages": 1,
            "totalNoOfRecords": 1,
        },
        request=_make_request(),
    )
    _, _, _, page_size = parse_paginated(response)
    assert page_size is None


def test_parse_reporter_paginated_extracts_content():
    response = httpx.Response(
        200,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": {
                "content": [{"id": 1}, {"id": 2}],
                "totalPages": 3,
                "totalElements": 25,
            },
        },
        request=_make_request(),
    )
    items, total_pages, total_records = parse_reporter_paginated(response)
    assert items == [{"id": 1}, {"id": 2}]
    assert total_pages == 3
    assert total_records == 25


def test_parse_reporter_paginated_defaults_missing_totals():
    response = httpx.Response(
        200,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": {"content": [{"id": 1}]},
        },
        request=_make_request(),
    )
    items, total_pages, total_records = parse_reporter_paginated(response)
    assert items == [{"id": 1}]
    assert total_pages == 1
    assert total_records == 1


def _make_bare_pageable(
    content: list[object],
    total_pages: int = 1,
    total_elements: int = 2,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "content": content,
            "pageable": {
                "sort": {"unsorted": False, "sorted": True, "empty": False},
                "pageSize": 20,
                "pageNumber": 0,
                "offset": 0,
                "paged": True,
                "unpaged": False,
            },
            "totalPages": total_pages,
            "totalElements": total_elements,
            "last": True,
            "sort": {"unsorted": False, "sorted": True, "empty": False},
            "first": True,
            "numberOfElements": len(content),
            "size": 20,
            "number": 0,
            "empty": not content,
        },
        request=_make_request(),
    )


def test_parse_pageable_extracts_content_and_totals():
    response = _make_bare_pageable(
        content=[{"id": 1}, {"id": 2}],
        total_pages=3,
        total_elements=42,
    )
    items, total_pages, total_records = parse_pageable(response)
    assert items == [{"id": 1}, {"id": 2}]
    assert total_pages == 3
    assert total_records == 42


def test_parse_pageable_ignores_envelope_status_code():
    response = httpx.Response(
        200,
        json={
            "statusCode": "5000",
            "message": "ignored",
            "content": [{"id": 1}],
            "totalPages": 1,
            "totalElements": 1,
        },
        request=_make_request(),
    )
    items, total_pages, total_records = parse_pageable(response)
    assert items == [{"id": 1}]
    assert total_pages == 1
    assert total_records == 1


def test_parse_pageable_raises_on_missing_content():
    response = httpx.Response(
        200,
        json={"totalPages": 1, "totalElements": 0},
        request=_make_request(),
    )
    with pytest.raises(ApiError) as exc_info:
        parse_pageable(response)
    assert "missing 'content'" in exc_info.value.message


def test_parse_pageable_raises_on_non_integer_totals():
    response = httpx.Response(
        200,
        json={
            "content": [],
            "totalPages": "1",
            "totalElements": None,
        },
        request=_make_request(),
    )
    with pytest.raises(ApiError) as exc_info:
        parse_pageable(response)
    assert "pagination fields are not integers" in exc_info.value.message


def test_parse_pageable_raises_on_http_error():
    with pytest.raises(ServerError):
        parse_pageable(_err_response(500, "boom"))


def test_parse_pageable_raises_api_error_on_non_json():
    with pytest.raises(ApiError):
        parse_pageable(_non_json_response())


def test_parse_raw_returns_json_body():
    response = httpx.Response(
        200,
        json={"key1": "value1", "key2": "value2"},
        request=_make_request(),
    )
    assert parse_raw(response) == {"key1": "value1", "key2": "value2"}


@pytest.mark.parametrize(
    "parser,status_code,exc",
    [
        pytest.param(parse_data, 404, NotFoundError, id="parse_data-404"),
        pytest.param(parse_paginated, 500, ServerError, id="parse_paginated-500"),
        pytest.param(
            parse_reporter_paginated,
            500,
            ServerError,
            id="parse_reporter_paginated-500",
        ),
        pytest.param(parse_raw, 404, NotFoundError, id="parse_raw-404"),
    ],
)
def test_parsers_raise_on_http_error(
    parser: Callable[[httpx.Response], object],
    status_code: int,
    exc: type[Exception],
):
    with pytest.raises(exc):
        parser(_err_response(status_code, "err"))


@pytest.mark.parametrize(
    "parser",
    [
        pytest.param(parse_data, id="parse_data"),
        pytest.param(parse_paginated, id="parse_paginated"),
        pytest.param(parse_reporter_paginated, id="parse_reporter_paginated"),
        pytest.param(parse_raw, id="parse_raw"),
    ],
)
def test_parsers_raise_api_error_on_non_json(
    parser: Callable[[httpx.Response], object],
):
    with pytest.raises(ApiError):
        parser(_non_json_response())


def test_parse_data_api_error_on_non_json_has_message():
    response = httpx.Response(
        200,
        content=b"<html>oops</html>",
        request=_make_request(),
    )
    with pytest.raises(ApiError) as exc_info:
        parse_data(response)
    assert "Invalid JSON response" in exc_info.value.message


def test_parse_data_raises_api_error_on_missing_data_key():
    response = httpx.Response(
        200,
        json={"statusCode": "1003"},
        request=_make_request(),
    )
    with pytest.raises(ApiError) as exc_info:
        parse_data(response)
    assert "missing 'data'" in exc_info.value.message


_ENVELOPE_PARSERS = (
    pytest.param(parse_data, id="parse_data"),
    pytest.param(parse_paginated, id="parse_paginated"),
    pytest.param(parse_reporter_paginated, id="parse_reporter_paginated"),
)


def test_single_fetch_no_data_surfaces_server_message_on_not_found():
    response = httpx.Response(
        200,
        json={"statusCode": "5000", "message": "No data found"},
        request=_make_request(),
    )
    with pytest.raises(NotFoundError) as exc_info:
        parse_data(response)
    assert exc_info.value.message == "No data found"
    assert exc_info.value.envelope_status_code == "5000"
    assert exc_info.value.envelope_message == "No data found"
    assert exc_info.value.status_code == 200


@pytest.mark.parametrize(
    "parser",
    [
        pytest.param(parse_paginated, id="parse_paginated"),
        pytest.param(parse_reporter_paginated, id="parse_reporter_paginated"),
    ],
)
def test_list_no_data_returns_empty_instead_of_raising(
    parser: Callable[[httpx.Response], tuple[object, ...]],
):
    response = httpx.Response(
        200,
        json={"statusCode": "5000", "message": "No data found"},
        request=_make_request(),
    )
    result = parser(response)
    assert result[0] == []


@pytest.mark.parametrize("parser", _ENVELOPE_PARSERS)
def test_envelope_error_without_message_uses_fallback(
    parser: Callable[[httpx.Response], object],
):
    response = httpx.Response(
        200,
        json={"statusCode": "5000"},
        request=_make_request(),
    )
    with pytest.raises(ApiError) as exc_info:
        parser(response)
    assert "5000" in exc_info.value.message
    assert "CloudAz error" in exc_info.value.message
    assert exc_info.value.envelope_status_code == "5000"
    assert exc_info.value.envelope_message is None


@pytest.mark.parametrize("parser", _ENVELOPE_PARSERS)
def test_envelope_error_with_empty_string_message_uses_fallback(
    parser: Callable[[httpx.Response], object],
):
    response = httpx.Response(
        200,
        json={"statusCode": "5000", "message": ""},
        request=_make_request(),
    )
    with pytest.raises(ApiError) as exc_info:
        parser(response)
    assert "5000" in exc_info.value.message
    assert exc_info.value.envelope_status_code == "5000"


def test_no_data_empty_page_skips_missing_pagination_keys():
    response = httpx.Response(
        200,
        json={"statusCode": "5000", "message": "No data found"},
        request=_make_request(),
    )
    data, total_pages, _, _ = parse_paginated(response)
    assert data == []
    assert total_pages == 0


def test_no_data_empty_page_skips_missing_data_key_on_reporter():
    response = httpx.Response(
        200,
        json={"statusCode": "5000", "message": "No data found"},
        request=_make_request(),
    )
    items, total_pages, _ = parse_reporter_paginated(response)
    assert items == []
    assert total_pages == 0


def test_parse_data_without_statusCode_falls_through_to_missing_data():
    response = httpx.Response(
        200,
        json={"message": "legacy body without statusCode"},
        request=_make_request(),
    )
    with pytest.raises(ApiError) as exc_info:
        parse_data(response)
    assert "missing 'data'" in exc_info.value.message
    assert exc_info.value.envelope_status_code is None


@pytest.mark.parametrize("success_code", ["1002", "1003", "1004"])
def test_success_envelope_codes_pass_through(success_code: str):
    response = httpx.Response(
        200,
        json={"statusCode": success_code, "message": "ok", "data": {"id": 1}},
        request=_make_request(),
    )
    assert parse_data(response) == {"id": 1}


def test_parse_raw_ignores_envelope_error_statusCode():
    response = httpx.Response(
        200,
        json={"statusCode": "5000", "message": "No data found"},
        request=_make_request(),
    )
    assert parse_raw(response) == {
        "statusCode": "5000",
        "message": "No data found",
    }


_ALL_PARSERS = (
    pytest.param(parse_data, id="parse_data"),
    pytest.param(parse_paginated, id="parse_paginated"),
    pytest.param(parse_reporter_paginated, id="parse_reporter_paginated"),
    pytest.param(parse_raw, id="parse_raw"),
)


@pytest.mark.parametrize("parser", _ALL_PARSERS)
def test_http_error_with_envelope_surfaces_server_message(
    parser: Callable[[httpx.Response], object],
):
    response = httpx.Response(
        400,
        json={
            "statusCode": "6000",
            "message": "An internal server error occurred.",
        },
        request=_make_request(),
    )
    from nextlabs_sdk.exceptions import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        parser(response)
    assert exc_info.value.message == "An internal server error occurred."
    assert exc_info.value.envelope_status_code == "6000"
    assert exc_info.value.envelope_message == "An internal server error occurred."
    assert exc_info.value.status_code == 400


@pytest.mark.parametrize("parser", _ALL_PARSERS)
def test_http_error_without_envelope_preserves_legacy_message(
    parser: Callable[[httpx.Response], object],
):
    response = httpx.Response(
        400,
        json={"foo": "bar"},
        request=_make_request(),
    )
    from nextlabs_sdk.exceptions import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        parser(response)
    assert exc_info.value.message == "HTTP 400"
    assert exc_info.value.envelope_status_code is None
    assert exc_info.value.envelope_message is None


@pytest.mark.parametrize("parser", _ALL_PARSERS)
def test_http_500_with_non_json_body_preserves_legacy_message(
    parser: Callable[[httpx.Response], object],
):
    response = httpx.Response(
        500,
        content=b"<html>boom</html>",
        request=_make_request(),
    )
    with pytest.raises(ServerError) as exc_info:
        parser(response)
    assert exc_info.value.message == "HTTP 500"
    assert exc_info.value.envelope_status_code is None


@pytest.mark.parametrize("parser", _ALL_PARSERS)
def test_http_404_with_envelope_uses_not_found_error(
    parser: Callable[[httpx.Response], object],
):
    response = httpx.Response(
        404,
        json={"statusCode": "5000", "message": "No data found"},
        request=_make_request(),
    )
    with pytest.raises(NotFoundError) as exc_info:
        parser(response)
    assert exc_info.value.message == "No data found"
    assert exc_info.value.envelope_status_code == "5000"
    assert exc_info.value.status_code == 404


@pytest.mark.parametrize("parser", _ALL_PARSERS)
def test_http_error_prefers_envelope_message_even_for_success_statuscode(
    parser: Callable[[httpx.Response], object],
):
    response = httpx.Response(
        400,
        json={"statusCode": "1003", "message": "odd but surfaced"},
        request=_make_request(),
    )
    from nextlabs_sdk.exceptions import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        parser(response)
    assert exc_info.value.message == "odd but surfaced"
    assert exc_info.value.envelope_status_code == "1003"


class _Item(BaseModel):
    id: int


def test_paginated_no_data_returns_empty_without_raising():
    data, total_pages, total_records, page_size = parse_paginated(_no_data_envelope())
    assert data == []
    assert total_pages == 0
    assert total_records == 0
    assert page_size == 0


def test_build_page_no_data_yields_empty_terminating_page():
    page = build_page(_no_data_envelope(), _Item, page_no=0)
    assert page.entries == []
    assert page.total_pages == 0
    assert page.total_records == 0


def test_reporter_paginated_no_data_returns_empty_without_raising():
    items, total_pages, total_records = parse_reporter_paginated(_no_data_envelope())
    assert items == []
    assert total_pages == 0
    assert total_records == 0


def test_single_fetch_no_data_raises_not_found_with_envelope_fields():
    with pytest.raises(NotFoundError) as exc_info:
        parse_data(_no_data_envelope())
    assert exc_info.value.envelope_status_code == "5000"
    assert exc_info.value.envelope_message == "No data found"
    assert exc_info.value.status_code == 200


@pytest.mark.parametrize(
    "message",
    [
        pytest.param("No Data Found", id="title-case"),
        pytest.param("the server reports: no data found for query", id="substring"),
    ],
)
def test_no_data_message_match_is_case_insensitive_substring(message: str):
    response = httpx.Response(
        200,
        json={"statusCode": "5000", "message": message},
        request=_make_request(),
    )
    with pytest.raises(NotFoundError):
        parse_data(response)
    data, _, _, _ = parse_paginated(response)
    assert data == []


def test_generic_5000_without_no_data_message_still_raises_api_error():
    response = httpx.Response(
        200,
        json={"statusCode": "5000", "message": "Something else broke"},
        request=_make_request(),
    )
    for parser in (parse_data, parse_paginated, parse_reporter_paginated):
        with pytest.raises(ApiError) as exc_info:
            parser(response)
        assert not isinstance(exc_info.value, NotFoundError)
        assert exc_info.value.envelope_status_code == "5000"


def test_other_non_success_code_still_raises_api_error():
    response = httpx.Response(
        200,
        json={"statusCode": "6000", "message": "No data found"},
        request=_make_request(),
    )
    for parser in (parse_data, parse_paginated, parse_reporter_paginated):
        with pytest.raises(ApiError) as exc_info:
            parser(response)
        assert not isinstance(exc_info.value, NotFoundError)
        assert exc_info.value.envelope_status_code == "6000"


def test_sync_and_async_pagination_handle_no_data_identically():
    def fetch(page_no: int) -> PageResult[_Item]:
        return build_page(_no_data_envelope(), _Item, page_no)

    sync_items = list(SyncPaginator(fetch))

    async def fetch_async(page_no: int) -> PageResult[_Item]:
        return build_page(_no_data_envelope(), _Item, page_no)

    async def collect() -> list[_Item]:
        return [item async for item in AsyncPaginator(fetch_async)]

    async_items = asyncio.run(collect())

    assert sync_items == async_items == []


def test_sync_and_async_single_fetch_raise_not_found_identically():
    sync_exc: type[Exception] | None = None
    try:
        parse_data(_no_data_envelope())
    except NotFoundError as err:
        sync_exc = type(err)

    async def fetch_async() -> object:
        return parse_data(_no_data_envelope())

    async_exc: type[Exception] | None = None
    try:
        asyncio.run(fetch_async())
    except NotFoundError as err:
        async_exc = type(err)

    assert sync_exc is NotFoundError
    assert async_exc is NotFoundError
