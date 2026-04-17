from __future__ import annotations

import json

import pytest
from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._component_type_models import (
    ComponentType,
    ComponentTypeType,
)
from nextlabs_sdk._cloudaz._component_type_search import (
    ComponentTypeSearchService,
)
from nextlabs_sdk._cloudaz._component_types import ComponentTypeService
from nextlabs_sdk._pagination import PageResult, SyncPaginator
from nextlabs_sdk.exceptions import NotFoundError

runner = CliRunner()

_GLOBAL_OPTS = (
    "--base-url",
    "https://example.com",
    "--username",
    "admin",
    "--password",
    "secret",
)


def _make_component_type(
    ct_id: int = 1,
    name: str = "File Server",
    short_name: str = "file_server",
) -> ComponentType:
    return ComponentType(
        id=ct_id,
        name=name,
        short_name=short_name,
        description="A file server",
        type=ComponentTypeType.RESOURCE,
        status="ACTIVE",
        tags=[],
        attributes=[],
        actions=[],
        obligations=[],
    )


def _make_paginator(items: list[ComponentType]) -> SyncPaginator[ComponentType]:
    page: PageResult[ComponentType] = PageResult(
        entries=items,
        page_no=0,
        page_size=len(items),
        total_pages=1,
        total_records=len(items),
    )

    def fetch_page(page_no: int) -> PageResult[ComponentType]:
        return page

    return SyncPaginator(fetch_page=fetch_page)


@pytest.fixture
def stub_client():
    mock_client = mock(CloudAzClient)
    mock_ct = mock(ComponentTypeService)
    mock_ct_search = mock(ComponentTypeSearchService)
    mock_client.component_types = mock_ct
    mock_client.component_type_search = mock_ct_search
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)
    return mock_client, mock_ct, mock_ct_search


@pytest.mark.parametrize(
    "as_json,check",
    [
        pytest.param(False, lambda out: "File Server" in out, id="table"),
        pytest.param(
            True,
            lambda out: json.loads(out)["name"] == "File Server",
            id="json",
        ),
    ],
)
def test_component_types_get(stub_client, as_json, check):
    _, mock_ct, _ = stub_client
    when(mock_ct).get(1).thenReturn(_make_component_type())

    args = list(_GLOBAL_OPTS)
    if as_json:
        args.append("--json")
    args.extend(["component-types", "get", "1"])

    result = runner.invoke(app, args)

    assert result.exit_code == 0
    assert check(result.output)


def test_component_types_get_not_found(stub_client):
    _, mock_ct, _ = stub_client
    when(mock_ct).get(999).thenRaise(NotFoundError(message="HTTP 404"))

    result = runner.invoke(app, [*_GLOBAL_OPTS, "component-types", "get", "999"])

    assert result.exit_code == 1
    assert "Not found" in result.output


def test_component_types_create_success(stub_client):
    _, mock_ct, _ = stub_client
    payload = {"name": "New Type", "shortName": "new", "type": "RESOURCE"}
    when(mock_ct).create(payload).thenReturn(42)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "component-types", "create", "--data", json.dumps(payload)],
    )

    assert result.exit_code == 0
    assert "42" in result.output


def test_component_types_create_invalid_json(stub_client):
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "component-types", "create", "--data", "not-json"],
    )

    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


def test_component_types_modify_success(stub_client):
    _, mock_ct, _ = stub_client
    payload = {"id": 1, "name": "Updated"}
    when(mock_ct).modify(payload).thenReturn(1)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "component-types", "modify", "--data", json.dumps(payload)],
    )

    assert result.exit_code == 0
    assert "Modified" in result.output


def test_component_types_delete_success(stub_client):
    _, mock_ct, _ = stub_client
    when(mock_ct).delete(1).thenReturn(None)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "component-types", "delete", "1"])

    assert result.exit_code == 0
    assert "Deleted" in result.output


def _json_list_has_file_server(out: str) -> bool:
    parsed = json.loads(out)
    return isinstance(parsed, list) and parsed[0]["name"] == "File Server"


@pytest.mark.parametrize(
    "extra_args,as_json,check",
    [
        pytest.param((), False, lambda out: "File Server" in out, id="table"),
        pytest.param((), True, _json_list_has_file_server, id="json"),
        pytest.param(
            (
                "--type",
                "RESOURCE",
                "--text",
                "file",
                "--tag",
                "dept",
                "--sort",
                "name",
                "--page-size",
                "50",
            ),
            False,
            lambda out: "File Server" in out,
            id="with-filters",
        ),
    ],
)
def test_component_types_search(stub_client, extra_args, as_json, check):
    _, _, mock_search = stub_client
    when(mock_search).search(...).thenReturn(_make_paginator([_make_component_type()]))

    args = list(_GLOBAL_OPTS)
    if as_json:
        args.append("--json")
    args.extend(["component-types", "search", *extra_args])

    result = runner.invoke(app, args)

    assert result.exit_code == 0
    assert check(result.output)
