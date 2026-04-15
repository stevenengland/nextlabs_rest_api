from __future__ import annotations

import httpx
from mockito import mock, when

from nextlabs_sdk._cloudaz._models import Operator
from nextlabs_sdk._cloudaz._operators import OperatorService

BASE_URL = "https://cloudaz.example.com"


def _make_request(path: str) -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_envelope(data: object) -> httpx.Response:
    return httpx.Response(
        200,
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
        request=_make_request("/console/api/v1/config/dataType/list"),
    )


def test_list_all_returns_operators() -> None:
    client = mock(httpx.Client)
    service = OperatorService(client)
    response = _make_envelope(
        [
            {"id": 1, "key": "eq", "label": "Equal", "dataType": "STRING"},
            {"id": 2, "key": "neq", "label": "Not Equal", "dataType": "STRING"},
        ]
    )
    when(client).get("/console/api/v1/config/dataType/list").thenReturn(response)

    result = service.list_all()

    assert len(result) == 2
    assert isinstance(result[0], Operator)
    assert result[0].key == "eq"
    assert result[1].key == "neq"


def test_list_by_type_returns_filtered_operators() -> None:
    client = mock(httpx.Client)
    service = OperatorService(client)
    response = _make_envelope(
        [
            {"id": 3, "key": "gt", "label": "Greater Than", "dataType": "NUMBER"},
        ]
    )
    when(client).get("/console/api/v1/config/dataType/list/NUMBER").thenReturn(response)

    result = service.list_by_type("NUMBER")

    assert len(result) == 1
    assert result[0].data_type == "NUMBER"


def test_list_types_returns_strings() -> None:
    client = mock(httpx.Client)
    service = OperatorService(client)
    response = _make_envelope(["STRING", "NUMBER", "DATE"])
    when(client).get("/console/api/v1/config/dataType/types").thenReturn(response)

    result = service.list_types()

    assert result == ["STRING", "NUMBER", "DATE"]


def test_list_all_empty() -> None:
    client = mock(httpx.Client)
    service = OperatorService(client)
    response = _make_envelope([])
    when(client).get("/console/api/v1/config/dataType/list").thenReturn(response)

    result = service.list_all()

    assert result == []
