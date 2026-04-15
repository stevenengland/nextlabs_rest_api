from __future__ import annotations

import httpx
import pytest

from nextlabs_sdk._cloudaz._response import parse_data, parse_paginated
from nextlabs_sdk.exceptions import NotFoundError, ServerError


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


def test_parse_data_extracts_data_field() -> None:
    response = _make_envelope(data={"id": 1, "name": "test"})
    result = parse_data(response)
    assert result == {"id": 1, "name": "test"}


def test_parse_data_extracts_list_data() -> None:
    response = _make_envelope(data=[{"id": 1}, {"id": 2}])
    result = parse_data(response)
    assert result == [{"id": 1}, {"id": 2}]


def test_parse_data_raises_on_http_error() -> None:
    response = httpx.Response(
        404,
        json={"message": "Not found"},
        request=_make_request(),
    )
    with pytest.raises(NotFoundError):
        parse_data(response)


def test_parse_paginated_extracts_all_fields() -> None:
    response = _make_envelope(
        data=[{"id": 1}],
        total_pages=5,
        total_records=42,
    )
    data, total_pages, total_records = parse_paginated(response)
    assert data == [{"id": 1}]
    assert total_pages == 5
    assert total_records == 42


def test_parse_paginated_raises_on_http_error() -> None:
    response = httpx.Response(
        500,
        json={"message": "Server error"},
        request=_make_request(),
    )
    with pytest.raises(ServerError):
        parse_paginated(response)
