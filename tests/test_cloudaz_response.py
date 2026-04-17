from __future__ import annotations

from typing import Callable

import httpx
import pytest

from nextlabs_sdk._cloudaz._response import (
    parse_data,
    parse_paginated,
    parse_raw,
    parse_reporter_paginated,
)
from nextlabs_sdk.exceptions import ApiError, NotFoundError, ServerError


def _make_request() -> httpx.Request:
    return httpx.Request("GET", "https://test/api")


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
    response = _make_envelope(data=[{"id": 1}], total_pages=5, total_records=42)
    data, total_pages, total_records = parse_paginated(response)
    assert data == [{"id": 1}]
    assert total_pages == 5
    assert total_records == 42


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


@pytest.mark.parametrize("parser", _ENVELOPE_PARSERS)
def test_envelope_error_surfaces_server_message(
    parser: Callable[[httpx.Response], object],
):
    response = httpx.Response(
        200,
        json={"statusCode": "5000", "message": "No data found"},
        request=_make_request(),
    )
    with pytest.raises(ApiError) as exc_info:
        parser(response)
    assert exc_info.value.message == "No data found"
    assert exc_info.value.envelope_status_code == "5000"
    assert exc_info.value.envelope_message == "No data found"
    assert exc_info.value.status_code == 200


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


def test_envelope_error_wins_over_missing_pagination_keys():
    response = httpx.Response(
        200,
        json={"statusCode": "5000", "message": "No data found"},
        request=_make_request(),
    )
    with pytest.raises(ApiError) as exc_info:
        parse_paginated(response)
    assert exc_info.value.message == "No data found"
    assert "totalPages" not in exc_info.value.message


def test_envelope_error_wins_over_missing_data_key_on_reporter():
    response = httpx.Response(
        200,
        json={"statusCode": "5000", "message": "No data found"},
        request=_make_request(),
    )
    with pytest.raises(ApiError) as exc_info:
        parse_reporter_paginated(response)
    assert exc_info.value.message == "No data found"


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
