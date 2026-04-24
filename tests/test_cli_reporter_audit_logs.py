from __future__ import annotations

import json
from typing import Any

import pytest
from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._reporter_audit_log_models import ReporterAuditLogEntry
from nextlabs_sdk._cloudaz._reporter_audit_logs import ReporterAuditLogService
from nextlabs_sdk._pagination import PageResult, SyncPaginator
from nextlabs_sdk.exceptions import NextLabsError

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
    mock_service = mock(ReporterAuditLogService)
    mock_client.reporter_audit_logs = mock_service
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)
    return mock_client, mock_service


def _entry(entry_id: int = 1) -> ReporterAuditLogEntry:
    return ReporterAuditLogEntry(
        id=entry_id,
        component="Monitor",
        created_by=10,
        created_date=1_700_000_000,
        hidden=False,
        last_updated=1_700_000_001,
        last_updated_by=10,
        msg_code="ACTIVITY_CREATED",
        msg_params="{}",
        owner_display_name="Alice",
        activity_msg="Created monitor",
    )


def _paginator(
    entries: list[ReporterAuditLogEntry],
) -> SyncPaginator[ReporterAuditLogEntry]:
    def fetch(page_no: int) -> PageResult[ReporterAuditLogEntry]:
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=1,
            total_records=len(entries),
        )

    return SyncPaginator(fetch_page=fetch)


def test_reporter_audit_logs_search_table(stub: tuple[Any, Any]) -> None:
    _, service = stub
    when(service).search(page_size=20).thenReturn(_paginator([_entry(42)]))

    result = runner.invoke(app, [*_GLOBAL_OPTS, "reporter-audit-logs", "search"])

    assert result.exit_code == 0
    assert "Monitor" in result.output
    assert "Alice" in result.output


def test_reporter_audit_logs_search_json(stub: tuple[Any, Any]) -> None:
    _, service = stub
    when(service).search(page_size=20).thenReturn(_paginator([_entry(42)]))

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "-o", "json", "reporter-audit-logs", "search"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload[0]["id"] == 42


def test_reporter_audit_logs_search_page_size(stub: tuple[Any, Any]) -> None:
    _, service = stub
    when(service).search(page_size=5).thenReturn(_paginator([_entry()]))

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "reporter-audit-logs", "search", "--page-size", "5"],
    )

    assert result.exit_code == 0


def test_reporter_audit_logs_search_wide_includes_extra_columns(
    stub: tuple[Any, Any],
) -> None:
    _, service = stub
    when(service).search(page_size=20).thenReturn(_paginator([_entry(42)]))

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--output", "wide", "reporter-audit-logs", "search"],
        env={"COLUMNS": "320"},
    )

    assert result.exit_code == 0, result.output
    output = result.output.replace("\n", " ")
    assert "Last Updated" in output
    assert "Msg Code" in output
    assert "Created By" in output
    assert "Last Updated By" in output
    assert "Hidden" in output
    assert "ACTIVITY_CREATED" in output


def test_reporter_audit_logs_search_error(stub: tuple[Any, Any]) -> None:
    _, service = stub
    when(service).search(page_size=20).thenRaise(NextLabsError("boom"))

    result = runner.invoke(app, [*_GLOBAL_OPTS, "reporter-audit-logs", "search"])

    assert result.exit_code == 1
    assert "boom" in result.output
