from __future__ import annotations

from typing import cast

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._models import Operator
from nextlabs_sdk._cloudaz._operators import OperatorService

BASE_URL = "https://cloudaz.example.com"
_LIST_ALL = "/console/api/v1/config/dataType/list"
_LIST_BY_TYPE = "/console/api/v1/config/dataType/list/NUMBER"
_LIST_TYPES = "/console/api/v1/config/dataType/types"


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
        request=httpx.Request("GET", f"{BASE_URL}{_LIST_ALL}"),
    )


@pytest.fixture
def service() -> tuple[OperatorService, httpx.Client]:
    client = cast(httpx.Client, mock(httpx.Client))
    return OperatorService(client), client


def test_list_all_returns_operators(
    service: tuple[OperatorService, httpx.Client],
) -> None:
    svc, client = service
    when(client).get(_LIST_ALL).thenReturn(
        _make_envelope(
            [
                {"id": 1, "key": "eq", "label": "Equal", "dataType": "STRING"},
                {"id": 2, "key": "neq", "label": "Not Equal", "dataType": "STRING"},
            ]
        )
    )

    result = svc.list_all()

    assert len(result) == 2
    assert isinstance(result[0], Operator)
    assert result[0].key == "eq"
    assert result[1].key == "neq"


def test_list_by_type_returns_filtered_operators(
    service: tuple[OperatorService, httpx.Client],
) -> None:
    svc, client = service
    when(client).get(_LIST_BY_TYPE).thenReturn(
        _make_envelope(
            [{"id": 3, "key": "gt", "label": "Greater Than", "dataType": "NUMBER"}]
        )
    )

    result = svc.list_by_type("NUMBER")

    assert len(result) == 1
    assert result[0].data_type == "NUMBER"


def test_list_types_returns_strings(
    service: tuple[OperatorService, httpx.Client],
) -> None:
    svc, client = service
    when(client).get(_LIST_TYPES).thenReturn(
        _make_envelope(["STRING", "NUMBER", "DATE"])
    )

    assert svc.list_types() == ["STRING", "NUMBER", "DATE"]


def test_list_all_empty(service: tuple[OperatorService, httpx.Client]) -> None:
    svc, client = service
    when(client).get(_LIST_ALL).thenReturn(_make_envelope([]))

    assert svc.list_all() == []
