from __future__ import annotations

import json
from typing import Any

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


def _stub_client() -> tuple[Any, Any, Any]:
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


def _make_policy_lite(
    policy_id: int = 82,
    name: str = "Allow IT Access",
) -> PolicyLite:
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


def _make_paginator(
    items: list[PolicyLite],
) -> SyncPaginator[PolicyLite]:
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


def test_policies_get_table() -> None:
    _, mock_policies, _ = _stub_client()
    policy = _make_policy()
    when(mock_policies).get(82).thenReturn(policy)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "get", "82"],
    )

    assert result.exit_code == 0
    assert "Allow IT Access" in result.output


def test_policies_get_json() -> None:
    _, mock_policies, _ = _stub_client()
    policy = _make_policy()
    when(mock_policies).get(82).thenReturn(policy)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--json", "policies", "get", "82"],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["name"] == "Allow IT Access"


def test_policies_get_not_found() -> None:
    _, mock_policies, _ = _stub_client()
    when(mock_policies).get(999).thenRaise(
        NotFoundError(message="HTTP 404"),
    )

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "get", "999"],
    )

    assert result.exit_code == 1
    assert "Not found" in result.output


def test_policies_create_success() -> None:
    _, mock_policies, _ = _stub_client()
    payload = {"name": "New Policy", "effectType": "ALLOW"}
    when(mock_policies).create(payload).thenReturn(100)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "policies",
            "create",
            "--data",
            json.dumps(payload),
        ],
    )

    assert result.exit_code == 0
    assert "100" in result.output


def test_policies_create_invalid_json() -> None:
    _stub_client()

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "create", "--data", "not-json"],
    )

    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


def test_policies_create_json_array_rejected() -> None:
    _stub_client()

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "create", "--data", "[1, 2]"],
    )

    assert result.exit_code == 1
    assert "must be an object" in result.output


def test_policies_modify_success() -> None:
    _, mock_policies, _ = _stub_client()
    payload = {"id": 82, "name": "Updated Policy"}
    when(mock_policies).modify(payload).thenReturn(82)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "policies",
            "modify",
            "--data",
            json.dumps(payload),
        ],
    )

    assert result.exit_code == 0
    assert "Modified" in result.output


def test_policies_delete_success() -> None:
    _, mock_policies, _ = _stub_client()
    when(mock_policies).delete(82).thenReturn(None)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "delete", "82"],
    )

    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_policies_search_table() -> None:
    _, _, mock_search = _stub_client()
    policy = _make_policy_lite()
    paginator = _make_paginator([policy])
    when(mock_search).search(...).thenReturn(paginator)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "search"],
    )

    assert result.exit_code == 0
    assert "Allow IT Access" in result.output


def test_policies_search_json() -> None:
    _, _, mock_search = _stub_client()
    policy = _make_policy_lite()
    paginator = _make_paginator([policy])
    when(mock_search).search(...).thenReturn(paginator)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--json", "policies", "search"],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["name"] == "Allow IT Access"


def test_policies_search_with_filters() -> None:
    _, _, mock_search = _stub_client()
    policy = _make_policy_lite()
    paginator = _make_paginator([policy])
    when(mock_search).search(...).thenReturn(paginator)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "policies",
            "search",
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
        ],
    )

    assert result.exit_code == 0
    assert "Allow IT Access" in result.output


def test_policies_deploy_success() -> None:
    _, mock_policies, _ = _stub_client()
    when(mock_policies).deploy(
        [{"id": 82, "push": False}],
    ).thenReturn([DeploymentResult(id=82, push_results=[])])

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "deploy", "82"],
    )

    assert result.exit_code == 0
    assert "Deployed" in result.output


def test_policies_deploy_with_push() -> None:
    _, mock_policies, _ = _stub_client()
    when(mock_policies).deploy(
        [{"id": 82, "push": True}],
    ).thenReturn([DeploymentResult(id=82, push_results=[])])

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "deploy", "82", "--push"],
    )

    assert result.exit_code == 0
    assert "Deployed" in result.output


def test_policies_undeploy_success() -> None:
    _, mock_policies, _ = _stub_client()
    when(mock_policies).undeploy([82]).thenReturn(None)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "undeploy", "82"],
    )

    assert result.exit_code == 0
    assert "Undeployed" in result.output


def test_policies_export_success() -> None:
    _, mock_policies, _ = _stub_client()
    when(mock_policies).export(
        [{"id": 82}],
        export_mode="PLAIN",
    ).thenReturn('{"policies": []}')

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "export", "82"],
    )

    assert result.exit_code == 0
    assert '{"policies": []}' in result.output


def test_policies_export_json_flag() -> None:
    _, mock_policies, _ = _stub_client()
    when(mock_policies).export(
        [{"id": 82}],
        export_mode="PLAIN",
    ).thenReturn('{"policies": []}')

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--json", "policies", "export", "82"],
    )

    assert result.exit_code == 0
    assert '{"policies": []}' in result.output


def test_policies_import_success(tmp_path: Any) -> None:
    _, mock_policies, _ = _stub_client()
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


def test_policies_import_file_not_found() -> None:
    _stub_client()

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
