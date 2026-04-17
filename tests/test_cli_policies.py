from __future__ import annotations

import json
from typing import Any

import pytest
from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._component_models import DeploymentResult
from nextlabs_sdk._cloudaz._policies import PolicyService
from nextlabs_sdk._cloudaz._policy_models import ImportResult, Policy, PolicyLite
from nextlabs_sdk._cloudaz._policy_search import PolicySearchService
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
    mock_policies = mock(PolicyService)
    mock_policy_search = mock(PolicySearchService)
    mock_client.policies = mock_policies
    mock_client.policy_search = mock_policy_search
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)
    return mock_client, mock_policies, mock_policy_search


def _make_policy() -> Policy:
    return Policy(
        id=82,
        name="Allow IT Access",
        status="DRAFT",
        effect_type="ALLOW",
        deployed=False,
    )


def _make_policy_lite(policy_id: int = 82, name: str = "Allow IT Access") -> PolicyLite:
    return PolicyLite(
        id=policy_id,
        folder_id=1,
        name=name,
        lowercase_name=name.lower(),
        policy_full_name=name,
        description="Allow IT dept access",
        status="DRAFT",
        effect_type="ALLOW",
        last_updated_date=0,
        created_date=0,
        has_parent=False,
        has_sub_policies=False,
        owner_id=1,
        owner_display_name="admin",
        modified_by_id=1,
        modified_by="admin",
        tags=[],
        no_of_tags=0,
        authorities=[],
        manual_deploy=False,
        deployment_time=0,
        deployed=False,
        revision_count=0,
        hide_more_details=False,
        deployment_pending=False,
    )


def _make_paginator(items: list[PolicyLite]) -> SyncPaginator[PolicyLite]:
    page = PageResult(
        entries=items,
        page_no=0,
        page_size=len(items),
        total_pages=1,
        total_records=len(items),
    )

    def fetch_page(page_no: int) -> PageResult[PolicyLite]:
        return page

    return SyncPaginator(fetch_page=fetch_page)


# --- get (table vs json) ---


@pytest.mark.parametrize(
    "flags,check",
    [
        pytest.param(
            (),
            lambda out: "Allow IT Access" in out,
            id="table",
        ),
        pytest.param(
            ("--json",),
            lambda out: json.loads(out)["name"] == "Allow IT Access",
            id="json",
        ),
    ],
)
def test_policies_get(
    stub: tuple[Any, Any, Any],
    flags: tuple[str, ...],
    check: Any,
) -> None:
    _, mock_policies, _ = stub
    when(mock_policies).get(82).thenReturn(_make_policy())

    result = runner.invoke(app, [*_GLOBAL_OPTS, *flags, "policies", "get", "82"])

    assert result.exit_code == 0
    assert check(result.output)


def test_policies_get_not_found(stub: tuple[Any, Any, Any]) -> None:
    _, mock_policies, _ = stub
    when(mock_policies).get(999).thenRaise(NotFoundError(message="HTTP 404"))

    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "get", "999"])

    assert result.exit_code == 1
    assert "Not found" in result.output


# --- create ---


def test_policies_create_success(stub: tuple[Any, Any, Any]) -> None:
    _, mock_policies, _ = stub
    payload = {"name": "New Policy", "effectType": "ALLOW"}
    when(mock_policies).create(payload).thenReturn(100)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "create", "--data", json.dumps(payload)],
    )

    assert result.exit_code == 0
    assert "100" in result.output


@pytest.mark.parametrize(
    "data,expected_msg",
    [
        pytest.param("not-json", "Invalid JSON", id="invalid-json"),
        pytest.param("[1, 2]", "must be an object", id="json-array-rejected"),
    ],
)
def test_policies_create_invalid_data(
    stub: tuple[Any, Any, Any],
    data: str,
    expected_msg: str,
) -> None:
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "create", "--data", data],
    )

    assert result.exit_code == 1
    assert expected_msg in result.output


def test_policies_modify_success(stub: tuple[Any, Any, Any]) -> None:
    _, mock_policies, _ = stub
    payload = {"id": 82, "name": "Updated Policy"}
    when(mock_policies).modify(payload).thenReturn(82)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "modify", "--data", json.dumps(payload)],
    )

    assert result.exit_code == 0
    assert "Modified" in result.output


def test_policies_delete_success(stub: tuple[Any, Any, Any]) -> None:
    _, mock_policies, _ = stub
    when(mock_policies).delete(82).thenReturn(None)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "delete", "82"])

    assert result.exit_code == 0
    assert "Deleted" in result.output


# --- search (table / json / with filters) ---


@pytest.mark.parametrize(
    "extra_args,check",
    [
        pytest.param(
            (),
            lambda out: "Allow IT Access" in out,
            id="table",
        ),
        pytest.param(
            ("--json",),
            lambda out: json.loads(out)[0]["name"] == "Allow IT Access",
            id="json",
        ),
        pytest.param(
            (
                "--status",
                "DRAFT",
                "--effect",
                "ALLOW",
                "--text",
                "IT",
                "--tag",
                "department",
                "--sort",
                "name",
                "--page-size",
                "50",
            ),
            lambda out: "Allow IT Access" in out,
            id="with-filters",
        ),
    ],
)
def test_policies_search(
    stub: tuple[Any, Any, Any],
    extra_args: tuple[str, ...],
    check: Any,
) -> None:
    _, _, mock_search = stub
    when(mock_search).search(...).thenReturn(_make_paginator([_make_policy_lite()]))

    json_flag = ("--json",) if "--json" in extra_args else ()
    positional_args = tuple(a for a in extra_args if a != "--json")

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, *json_flag, "policies", "search", *positional_args],
    )

    assert result.exit_code == 0
    assert check(result.output)


# --- deploy / undeploy ---


@pytest.mark.parametrize(
    "extra_args,expected_call",
    [
        pytest.param((), [{"id": 82, "push": False}], id="default"),
        pytest.param(("--push",), [{"id": 82, "push": True}], id="with-push"),
    ],
)
def test_policies_deploy(
    stub: tuple[Any, Any, Any],
    extra_args: tuple[str, ...],
    expected_call: list[dict[str, Any]],
) -> None:
    _, mock_policies, _ = stub
    when(mock_policies).deploy(expected_call).thenReturn(
        [DeploymentResult(id=82, push_results=[])],
    )

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "deploy", "82", *extra_args],
    )

    assert result.exit_code == 0
    assert "Deployed" in result.output


def test_policies_undeploy_success(stub: tuple[Any, Any, Any]) -> None:
    _, mock_policies, _ = stub
    when(mock_policies).undeploy([82]).thenReturn(None)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "policies", "undeploy", "82"])

    assert result.exit_code == 0
    assert "Undeployed" in result.output


# --- export / import ---


@pytest.mark.parametrize("json_flag", [(), ("--json",)], ids=["plain", "json-flag"])
def test_policies_export_success(
    stub: tuple[Any, Any, Any],
    json_flag: tuple[str, ...],
) -> None:
    _, mock_policies, _ = stub
    when(mock_policies).export([{"id": 82}], export_mode="PLAIN").thenReturn(
        '{"policies": []}',
    )

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, *json_flag, "policies", "export", "82"],
    )

    assert result.exit_code == 0
    assert '{"policies": []}' in result.output


def test_policies_import_success(stub: tuple[Any, Any, Any], tmp_path: Any) -> None:
    _, mock_policies, _ = stub
    import_file = tmp_path / "policies.bin"
    import_file.write_bytes(b"file-content")
    when(mock_policies).import_policies(
        ...,
        import_mechanism="PARTIAL",
        cleanup=False,
    ).thenReturn(
        ImportResult(
            total_components=0,
            total_policies=1,
            total_policy_models=0,
            non_blocking_error=False,
        ),
    )

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "policies",
            "import-policies",
            "--file",
            str(import_file),
        ],
    )

    assert result.exit_code == 0
    assert "Imported" in result.output
    assert "1 policies" in result.output


def test_policies_import_file_not_found(stub: tuple[Any, Any, Any]) -> None:
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "policies",
            "import-policies",
            "--file",
            "/nonexistent/path/file.bin",
        ],
    )

    assert result.exit_code == 1
    assert "File not found" in result.output
