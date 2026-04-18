from __future__ import annotations

import json
from typing import Any

import pytest
from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._models import Operator
from nextlabs_sdk._cloudaz._operators import OperatorService

runner = CliRunner()

_GLOBAL_OPTS = (
    "--base-url",
    "https://example.com",
    "--username",
    "admin",
    "--password",
    "secret",
)


@pytest.fixture
def stub() -> tuple[Any, Any]:
    mock_client = mock(CloudAzClient)
    mock_service = mock(OperatorService)
    mock_client.operators = mock_service
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)
    return mock_client, mock_service


def _make_operator(
    op_id: int = 1,
    key: str = "eq",
    label: str = "Equals",
    data_type: str = "string",
) -> Operator:
    return Operator(id=op_id, key=key, label=label, data_type=data_type)


def test_operators_list_table(stub: tuple[Any, Any]) -> None:
    _, service = stub
    when(service).list_all().thenReturn(
        [_make_operator(1, "eq", "Equals", "string")],
    )

    result = runner.invoke(app, [*_GLOBAL_OPTS, "operators", "list"])

    assert result.exit_code == 0
    assert "eq" in result.output
    assert "Equals" in result.output


def test_operators_list_json(stub: tuple[Any, Any]) -> None:
    _, service = stub
    when(service).list_all().thenReturn([_make_operator()])

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "-o", "json", "operators", "list"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload[0]["key"] == "eq"


def test_operators_list_by_type(stub: tuple[Any, Any]) -> None:
    _, service = stub
    when(service).list_by_type("integer").thenReturn(
        [_make_operator(2, "gt", "Greater Than", "integer")],
    )

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "operators", "list-by-type", "integer"],
    )

    assert result.exit_code == 0
    assert "gt" in result.output
    assert "Greater Than" in result.output


def test_operators_list_types_table(stub: tuple[Any, Any]) -> None:
    _, service = stub
    when(service).list_types().thenReturn(["string", "integer", "date"])

    result = runner.invoke(app, [*_GLOBAL_OPTS, "operators", "list-types"])

    assert result.exit_code == 0
    assert "string" in result.output
    assert "integer" in result.output
    assert "date" in result.output


def test_operators_list_types_json(stub: tuple[Any, Any]) -> None:
    _, service = stub
    when(service).list_types().thenReturn(["string", "integer"])

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "-o", "json", "operators", "list-types"],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == ["string", "integer"]
