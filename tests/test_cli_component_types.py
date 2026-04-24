from __future__ import annotations

import json

import pytest
from mockito import mock, when
from strip_ansi import strip_ansi
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
        args.extend(["--output", "json"])
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


def test_component_types_create_success(stub_client, tmp_path):
    _, mock_ct, _ = stub_client
    payload = {"name": "New Type", "shortName": "new", "type": "RESOURCE"}
    when(mock_ct).create(payload).thenReturn(42)
    payload_path = tmp_path / "ct.json"
    payload_path.write_text(json.dumps(payload))

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "component-types", "create", "--payload", str(payload_path)],
    )

    assert result.exit_code == 0
    assert "42" in result.output


def test_component_types_create_invalid_payload(stub_client, tmp_path):
    payload_path = tmp_path / "bad.json"
    payload_path.write_text("not-json")

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "component-types", "create", "--payload", str(payload_path)],
    )

    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


def test_component_types_create_rejects_deprecated_data_flag(stub_client):
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "component-types", "create", "--data", "{}"],
    )

    assert result.exit_code == 1
    assert "--payload" in result.output


def test_component_types_modify_success(stub_client, tmp_path):
    _, mock_ct, _ = stub_client
    payload = {"id": 1, "name": "Updated"}
    when(mock_ct).modify(payload).thenReturn(1)
    payload_path = tmp_path / "mod.json"
    payload_path.write_text(json.dumps(payload))

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "component-types", "modify", "--payload", str(payload_path)],
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
        args.extend(["--output", "json"])
    args.extend(["component-types", "search", *extra_args])

    result = runner.invoke(app, args)

    assert result.exit_code == 0
    assert check(result.output)


def test_component_types_get_active(stub_client):
    _, mock_ct, _ = stub_client
    when(mock_ct).get_active(1).thenReturn(_make_component_type())

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "component-types", "get-active", "1"],
    )

    assert result.exit_code == 0, result.output
    assert "File Server" in result.output


def test_component_types_bulk_delete(stub_client):
    _, mock_ct, _ = stub_client
    when(mock_ct).bulk_delete([3, 4]).thenReturn(None)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "component-types", "bulk-delete", "--ids", "3,4"],
    )

    assert result.exit_code == 0, result.output
    assert "Deleted 2 component types" in strip_ansi(result.output)


def test_component_types_clone(stub_client):
    _, mock_ct, _ = stub_client
    when(mock_ct).clone(5).thenReturn(42)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "component-types", "clone", "5"])

    assert result.exit_code == 0, result.output
    assert "42" in result.output


def _make_component_type_rich(ct_id: int = 7) -> ComponentType:
    return ComponentType.model_validate(
        {
            "id": ct_id,
            "name": "File Server",
            "shortName": "file_server",
            "description": "A file server component type",
            "type": "RESOURCE",
            "status": "ACTIVE",
            "tags": [],
            "attributes": [],
            "actions": [],
            "obligations": [],
            "version": 3,
            "ownerDisplayName": "ops-team",
            "createdDate": 1_700_000_000_000,
            "lastUpdatedDate": 1_700_100_000_000,
        },
    )


def test_component_types_get_wide_includes_extra_columns(stub_client):
    _, mock_ct, _ = stub_client
    when(mock_ct).get(7).thenReturn(_make_component_type_rich())

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--output", "wide", "component-types", "get", "7"],
        env={"COLUMNS": "320"},
    )

    assert result.exit_code == 0, result.output
    output = result.output.replace("\n", " ")
    assert "Description" in output
    assert "Owner" in output
    assert "Created" in output
    assert "Updated" in output
    assert "Version" in output
    assert "ops-team" in output
    assert "1700000000000" in output


def test_component_types_get_active_wide_includes_extra_columns(stub_client):
    _, mock_ct, _ = stub_client
    when(mock_ct).get_active(7).thenReturn(_make_component_type_rich())

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--output", "wide", "component-types", "get-active", "7"],
        env={"COLUMNS": "320"},
    )

    assert result.exit_code == 0, result.output
    output = result.output.replace("\n", " ")
    assert "Description" in output
    assert "Owner" in output
    assert "ops-team" in output


def test_component_types_search_wide_includes_extra_columns(stub_client):
    _, _, mock_search = stub_client
    when(mock_search).search(...).thenReturn(
        _make_paginator([_make_component_type_rich()]),
    )

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--output", "wide", "component-types", "search"],
        env={"COLUMNS": "320"},
    )

    assert result.exit_code == 0, result.output
    output = result.output.replace("\n", " ")
    assert "Description" in output
    assert "Owner" in output
    assert "Version" in output


def test_component_types_list_extra_subject_attributes_wide(stub_client):
    from nextlabs_sdk._cloudaz._component_type_models import AttributeConfig

    _, mock_ct, _ = stub_client
    when(mock_ct).list_extra_subject_attributes("USER").thenReturn(
        [
            AttributeConfig.model_validate(
                {
                    "id": 1,
                    "name": "Department",
                    "shortName": "dept",
                    "dataType": "STRING",
                    "sortOrder": 0,
                    "regExPattern": "^[A-Z]+$",
                    "version": 2,
                },
            ),
        ],
    )

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "--output",
            "wide",
            "component-types",
            "list-extra-subject-attributes",
            "USER",
        ],
        env={"COLUMNS": "240"},
    )

    assert result.exit_code == 0, result.output
    output = result.output.replace("\n", " ")
    assert "Regex Pattern" in output
    assert "Version" in output
    assert "^[A-Z]+$" in output


def test_component_types_list_extra_subject_attributes(stub_client):
    from nextlabs_sdk._cloudaz._component_type_models import AttributeConfig

    _, mock_ct, _ = stub_client
    when(mock_ct).list_extra_subject_attributes("USER").thenReturn(
        [
            AttributeConfig.model_validate(
                {
                    "id": 1,
                    "name": "Department",
                    "shortName": "dept",
                    "dataType": "STRING",
                    "sortOrder": 0,
                },
            ),
        ],
    )

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "component-types",
            "list-extra-subject-attributes",
            "USER",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Department" in result.output
