from __future__ import annotations

import json
from typing import Any

import pytest
from mockito import mock, when
from strip_ansi import strip_ansi
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._component_models import (
    Component,
    ComponentGroupType,
    ComponentLite,
    ComponentStatus,
    DeploymentResult,
)
from nextlabs_sdk._cloudaz._component_search import ComponentSearchService
from nextlabs_sdk._cloudaz._components import ComponentService
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


@pytest.fixture
def stub() -> tuple[Any, Any, Any]:
    mock_client = mock(CloudAzClient)
    mock_comp = mock(ComponentService)
    mock_comp_search = mock(ComponentSearchService)
    mock_client.components = mock_comp
    mock_client.component_search = mock_comp_search
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)
    return mock_client, mock_comp, mock_comp_search


def _make_component() -> Component:
    return Component(
        id=1,
        name="Host Name",
        description="A host name component",
        type=ComponentGroupType.RESOURCE,
        status=ComponentStatus.APPROVED,
        deployed=True,
    )


def _make_component_lite() -> ComponentLite:
    return ComponentLite(
        id=10,
        name="Resource Comp",
        status=ComponentStatus.DRAFT,
        group=ComponentGroupType.RESOURCE,
        deployed=False,
        model_id=100,
        model_type="RESOURCE",
        last_updated_date=0,
        created_date=0,
    )


def _make_paginator(items: list[ComponentLite]) -> SyncPaginator[ComponentLite]:
    page = PageResult(
        entries=items,
        page_no=0,
        page_size=len(items),
        total_pages=1,
        total_records=len(items),
    )

    def fetch_page(page_no: int) -> PageResult[ComponentLite]:
        return page

    return SyncPaginator(fetch_page=fetch_page)


def _invoke(*extra: str) -> Any:
    return runner.invoke(app, [*_GLOBAL_OPTS, *extra], env={"COLUMNS": "200"})


@pytest.mark.parametrize(
    "extra_opts,check",
    [
        pytest.param(
            ("components", "get", "1"),
            lambda r: "Host Name" in r.output,
            id="table",
        ),
        pytest.param(
            ("--output", "json", "components", "get", "1"),
            lambda r: json.loads(r.output)["name"] == "Host Name",
            id="json",
        ),
    ],
)
def test_components_get(
    stub: tuple[Any, Any, Any], extra_opts: tuple[str, ...], check: Any
):
    _, mock_comp, _ = stub
    when(mock_comp).get(1).thenReturn(_make_component())

    result = _invoke(*extra_opts)

    assert result.exit_code == 0
    assert check(result)


def test_components_get_not_found(stub: tuple[Any, Any, Any]):
    _, mock_comp, _ = stub
    when(mock_comp).get(999).thenRaise(NotFoundError(message="HTTP 404"))

    result = _invoke("components", "get", "999")

    assert result.exit_code == 1
    assert "Not found" in result.output


def test_components_create_success(stub: tuple[Any, Any, Any], tmp_path: Any):
    _, mock_comp, _ = stub
    payload = {"name": "New Comp", "type": "RESOURCE"}
    when(mock_comp).create(payload).thenReturn(42)
    payload_path = tmp_path / "comp.json"
    payload_path.write_text(json.dumps(payload))

    result = _invoke("components", "create", "--payload", str(payload_path))

    assert result.exit_code == 0
    assert "42" in result.output


def test_components_create_invalid_payload(stub: tuple[Any, Any, Any], tmp_path: Any):
    payload_path = tmp_path / "bad.json"
    payload_path.write_text("not-json")

    result = _invoke("components", "create", "--payload", str(payload_path))

    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


def test_components_create_rejects_deprecated_data_flag(stub: tuple[Any, Any, Any]):
    result = _invoke("components", "create", "--data", "{}")

    assert result.exit_code == 1
    assert "--payload" in result.output


def test_components_modify_success(stub: tuple[Any, Any, Any], tmp_path: Any):
    _, mock_comp, _ = stub
    payload = {"id": 1, "name": "Updated"}
    when(mock_comp).modify(payload).thenReturn(1)
    payload_path = tmp_path / "mod.json"
    payload_path.write_text(json.dumps(payload))

    result = _invoke("components", "modify", "--payload", str(payload_path))

    assert result.exit_code == 0
    assert "Modified" in result.output


def test_components_delete_success(stub: tuple[Any, Any, Any]):
    _, mock_comp, _ = stub
    when(mock_comp).delete(1).thenReturn(None)

    result = _invoke("components", "delete", "1")

    assert result.exit_code == 0
    assert "Deleted" in result.output


@pytest.mark.parametrize(
    "extra_opts,check",
    [
        pytest.param(
            ("components", "search"),
            lambda r: "Resource Comp" in r.output,
            id="table",
        ),
        pytest.param(
            ("--output", "json", "components", "search"),
            lambda r: json.loads(r.output)[0]["name"] == "Resource Comp",
            id="json",
        ),
        pytest.param(
            (
                "components",
                "search",
                "--group",
                "RESOURCE",
                "--status",
                "DRAFT",
                "--text",
                "host",
                "--sort",
                "name",
                "--page-size",
                "50",
            ),
            lambda r: "Resource Comp" in r.output,
            id="with-filters",
        ),
    ],
)
def test_components_search(
    stub: tuple[Any, Any, Any],
    extra_opts: tuple[str, ...],
    check: Any,
):
    _, _, mock_search = stub
    when(mock_search).search(...).thenReturn(_make_paginator([_make_component_lite()]))

    result = _invoke(*extra_opts)

    assert result.exit_code == 0
    assert check(result)


@pytest.mark.parametrize(
    "extra_opts,deploy_request",
    [
        pytest.param(
            ("components", "deploy", "5"),
            [{"id": 5, "push": False}],
            id="without-push",
        ),
        pytest.param(
            ("components", "deploy", "5", "--push"),
            [{"id": 5, "push": True}],
            id="with-push",
        ),
    ],
)
def test_components_deploy_success(
    stub: tuple[Any, Any, Any],
    extra_opts: tuple[str, ...],
    deploy_request: list[dict[str, object]],
):
    _, mock_comp, _ = stub
    when(mock_comp).deploy(deploy_request).thenReturn(
        [DeploymentResult(id=5, push_results=[])],
    )

    result = _invoke(*extra_opts)

    assert result.exit_code == 0
    assert "Deployed" in result.output


def test_components_get_wide_includes_extra_columns(stub: tuple[Any, Any, Any]):
    _, mock_comp, _ = stub
    when(mock_comp).get(1).thenReturn(_make_component())

    result = _invoke("--output", "wide", "components", "get", "1")

    assert result.exit_code == 0
    assert "Created" in result.output
    assert "Updated" in result.output
    assert "Owner" in result.output
    assert "Version" in result.output


def test_components_search_wide_includes_extra_columns(stub: tuple[Any, Any, Any]):
    _, _, mock_search = stub
    when(mock_search).search(...).thenReturn(_make_paginator([_make_component_lite()]))

    result = _invoke("--output", "wide", "components", "search")

    assert result.exit_code == 0
    assert "Created" in result.output
    assert "Updated" in result.output
    assert "Owner" in result.output
    assert "Version" in result.output


def test_components_undeploy_success(stub: tuple[Any, Any, Any]):
    _, mock_comp, _ = stub
    when(mock_comp).undeploy([5]).thenReturn(None)

    result = _invoke("components", "undeploy", "5")

    assert result.exit_code == 0
    assert "Undeployed" in result.output


def test_components_get_active(stub: tuple[Any, Any, Any]) -> None:
    _, mock_comp, _ = stub
    when(mock_comp).get_active(1).thenReturn(_make_component())

    result = runner.invoke(app, [*_GLOBAL_OPTS, "components", "get-active", "1"])

    assert result.exit_code == 0, result.output


def test_components_create_sub_success(
    stub: tuple[Any, Any, Any],
    tmp_path: Any,
) -> None:
    _, mock_comp, _ = stub
    payload = {"name": "Child"}
    when(mock_comp).create_sub_component({**payload, "parentId": 9}).thenReturn(200)
    payload_path = tmp_path / "s.json"
    payload_path.write_text(json.dumps(payload))

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "components",
            "create-sub",
            "--parent-id",
            "9",
            "--payload",
            str(payload_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "200" in result.output


def test_components_bulk_delete(stub: tuple[Any, Any, Any]) -> None:
    _, mock_comp, _ = stub
    when(mock_comp).bulk_delete([1, 2]).thenReturn(None)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "components", "bulk-delete", "--ids", "1,2"],
    )

    assert result.exit_code == 0, result.output
    assert "Deleted 2 components" in strip_ansi(result.output)


def test_components_find_dependencies(stub: tuple[Any, Any, Any]) -> None:
    from nextlabs_sdk._cloudaz._component_models import Dependency

    _, mock_comp, _ = stub
    when(mock_comp).find_dependencies([4]).thenReturn(
        [Dependency(id=77, type="POLICY", name="PolA")],
    )

    result = runner.invoke(app, [*_GLOBAL_OPTS, "components", "find-dependencies", "4"])

    assert result.exit_code == 0, result.output
    assert "PolA" in result.output
