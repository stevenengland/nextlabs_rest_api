from __future__ import annotations

import json
from typing import Any

import pytest
from mockito import mock, when
from strip_ansi import strip_ansi
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cloudaz._audit_log_models import AuditLogEntry
from nextlabs_sdk._cloudaz._audit_logs import EntityAuditLogService
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._pagination import PageResult, SyncPaginator

runner = CliRunner()

_GLOBAL_OPTS = (
    "--base-url",
    "https://example.com",
    "--username",
    "admin",
    "--password",
    "secret",
)
_DATE_OPTS = (
    "--start-date",
    "1700000000000",
    "--end-date",
    "1700100000000",
)


def _stub_client() -> tuple[Any, Any]:
    mock_client = mock(CloudAzClient)
    mock_audit = mock(EntityAuditLogService)
    mock_client.audit_logs = mock_audit
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)
    return mock_client, mock_audit


def _make_entry(
    entry_id: int = 1,
    action: str = "UPDATE",
    actor: str = "admin",
    entity_type: str = "POLICY",
) -> AuditLogEntry:
    return AuditLogEntry.model_validate(
        {
            "id": entry_id,
            "timestamp": 1700000000000,
            "action": action,
            "actorId": 100,
            "actor": actor,
            "entityType": entity_type,
            "entityId": 42,
        }
    )


def _make_paginator(entries: list[AuditLogEntry]) -> SyncPaginator[AuditLogEntry]:
    page = PageResult(
        entries=entries,
        page_no=0,
        page_size=len(entries),
        total_pages=1,
        total_records=len(entries),
    )

    def fetch_page(page_no: int) -> PageResult[AuditLogEntry]:
        return page

    return SyncPaginator(fetch_page=fetch_page)


@pytest.fixture
def stubbed_audit():
    _, mock_audit = _stub_client()
    return mock_audit


def _check_table(output: str) -> bool:
    return all(s in output for s in ("UPDATE", "admin", "POLICY"))


def _check_json(output: str) -> bool:
    parsed = json.loads(output)
    return (
        isinstance(parsed, list)
        and parsed[0]["action"] == "UPDATE"
        and parsed[0]["actor"] == "admin"
        and parsed[0]["entity_type"] == "POLICY"
    )


@pytest.mark.parametrize(
    "extra_global,check",
    [
        pytest.param((), _check_table, id="table"),
        pytest.param(
            (
                "--output",
                "json",
            ),
            _check_json,
            id="json",
        ),
    ],
)
def test_search_output_formats(stubbed_audit, extra_global, check):
    when(stubbed_audit).search(...).thenReturn(_make_paginator([_make_entry()]))

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, *extra_global, "audit-logs", "search", *_DATE_OPTS],
    )

    assert result.exit_code == 0
    assert check(result.output)


def test_search_with_filter_options(stubbed_audit):
    entry = _make_entry(action="CREATE", entity_type="COMPONENT")
    when(stubbed_audit).search(...).thenReturn(_make_paginator([entry]))

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "audit-logs",
            "search",
            *_DATE_OPTS,
            "--entity-type",
            "COMPONENT",
            "--action",
            "CREATE",
            "--page-size",
            "10",
            "--sort-by",
            "timestamp",
            "--sort-order",
            "descending",
        ],
    )

    assert result.exit_code == 0
    assert "CREATE" in result.output
    assert "COMPONENT" in result.output


def test_search_missing_required_dates():
    _stub_client()

    result = runner.invoke(app, [*_GLOBAL_OPTS, "audit-logs", "search"])

    assert result.exit_code != 0
    output = strip_ansi(result.output).lower()
    assert "start-date" in output or "start_date" in output


def test_audit_logs_export_with_ids(stubbed_audit: Any, tmp_path: Any) -> None:
    from nextlabs_sdk._cloudaz._audit_log_models import ExportAuditLogsRequest

    when(stubbed_audit).export(
        ExportAuditLogsRequest(ids=[1, 2], query=None),
    ).thenReturn(b"csv")

    out = tmp_path / "out.csv"
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "audit-logs",
            "export",
            "--ids",
            "1,2",
            "--output",
            str(out),
        ],
    )

    assert result.exit_code == 0, result.output
    assert out.read_bytes() == b"csv"


def test_audit_logs_export_with_query(stubbed_audit: Any, tmp_path: Any) -> None:
    when(stubbed_audit).export(...).thenReturn(b"csv-q")

    query_file = tmp_path / "q.json"
    query_file.write_text(
        json.dumps({"start_date": 1700000000000, "end_date": 1700100000000}),
    )
    out = tmp_path / "out.csv"

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "audit-logs",
            "export",
            "--query",
            str(query_file),
            "--output",
            str(out),
        ],
    )

    assert result.exit_code == 0, result.output
    assert out.read_bytes() == b"csv-q"


def test_audit_logs_export_requires_input(stubbed_audit: Any, tmp_path: Any) -> None:
    out = tmp_path / "out.csv"
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "audit-logs", "export", "--output", str(out)],
    )

    assert result.exit_code == 1
    assert "Provide" in result.output


def test_audit_logs_list_users(stubbed_audit: Any) -> None:
    from nextlabs_sdk._cloudaz._audit_log_models import AuditLogUser

    when(stubbed_audit).list_users().thenReturn(
        [
            AuditLogUser.model_validate(
                {"firstName": "Ada", "lastName": "Lovelace", "username": "ada"}
            )
        ],
    )

    result = runner.invoke(app, [*_GLOBAL_OPTS, "audit-logs", "list-users"])

    assert result.exit_code == 0, result.output
    assert "ada" in result.output
