from __future__ import annotations

import json
from typing import Any

from mockito import mock, when
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


def _stub_client() -> tuple[Any, Any, Any]:
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


def _make_paginator(
    items: list[ComponentLite],
) -> SyncPaginator[ComponentLite]:
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


def test_components_get_table() -> None:
    _, mock_comp, _ = _stub_client()
    comp = _make_component()
    when(mock_comp).get(1).thenReturn(comp)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "components", "get", "1"],
    )

    assert result.exit_code == 0
    assert "Host Name" in result.output


def test_components_get_json() -> None:
    _, mock_comp, _ = _stub_client()
    comp = _make_component()
    when(mock_comp).get(1).thenReturn(comp)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--json", "components", "get", "1"],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["name"] == "Host Name"


def test_components_get_not_found() -> None:
    _, mock_comp, _ = _stub_client()
    when(mock_comp).get(999).thenRaise(
        NotFoundError(message="HTTP 404"),
    )

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "components", "get", "999"],
    )

    assert result.exit_code == 1
    assert "Not found" in result.output


def test_components_create_success() -> None:
    _, mock_comp, _ = _stub_client()
    payload = {"name": "New Comp", "type": "RESOURCE"}
    when(mock_comp).create(payload).thenReturn(42)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "components",
            "create",
            "--data",
            json.dumps(payload),
        ],
    )

    assert result.exit_code == 0
    assert "42" in result.output


def test_components_create_invalid_json() -> None:
    _stub_client()

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "components", "create", "--data", "not-json"],
    )

    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


def test_components_modify_success() -> None:
    _, mock_comp, _ = _stub_client()
    payload = {"id": 1, "name": "Updated"}
    when(mock_comp).modify(payload).thenReturn(1)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "components",
            "modify",
            "--data",
            json.dumps(payload),
        ],
    )

    assert result.exit_code == 0
    assert "Modified" in result.output


def test_components_delete_success() -> None:
    _, mock_comp, _ = _stub_client()
    when(mock_comp).delete(1).thenReturn(None)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "components", "delete", "1"],
    )

    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_components_search_table() -> None:
    _, _, mock_search = _stub_client()
    comp = _make_component_lite()
    paginator = _make_paginator([comp])
    when(mock_search).search(...).thenReturn(paginator)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "components", "search"],
    )

    assert result.exit_code == 0
    assert "Resource Comp" in result.output


def test_components_search_json() -> None:
    _, _, mock_search = _stub_client()
    comp = _make_component_lite()
    paginator = _make_paginator([comp])
    when(mock_search).search(...).thenReturn(paginator)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--json", "components", "search"],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["name"] == "Resource Comp"


def test_components_search_with_filters() -> None:
    _, _, mock_search = _stub_client()
    comp = _make_component_lite()
    paginator = _make_paginator([comp])
    when(mock_search).search(...).thenReturn(paginator)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
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
        ],
    )

    assert result.exit_code == 0
    assert "Resource Comp" in result.output


def test_components_deploy_success() -> None:
    _, mock_comp, _ = _stub_client()
    when(mock_comp).deploy(
        [{"id": 5, "push": False}],
    ).thenReturn([DeploymentResult(id=5, push_results=[])])

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "components", "deploy", "5"],
    )

    assert result.exit_code == 0
    assert "Deployed" in result.output


def test_components_deploy_with_push() -> None:
    _, mock_comp, _ = _stub_client()
    when(mock_comp).deploy(
        [{"id": 5, "push": True}],
    ).thenReturn([DeploymentResult(id=5, push_results=[])])

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "components", "deploy", "5", "--push"],
    )

    assert result.exit_code == 0
    assert "Deployed" in result.output


def test_components_undeploy_success() -> None:
    _, mock_comp, _ = _stub_client()
    when(mock_comp).undeploy([5]).thenReturn(None)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "components", "undeploy", "5"],
    )

    assert result.exit_code == 0
    assert "Undeployed" in result.output
