from __future__ import annotations

import json
from typing import Any

from mockito import mock, when
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


def _make_paginator(
    entries: list[AuditLogEntry],
) -> SyncPaginator[AuditLogEntry]:
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


def test_search_table_output() -> None:
    _, mock_audit = _stub_client()
    entry = _make_entry()
    paginator = _make_paginator([entry])
    when(mock_audit).search(...).thenReturn(paginator)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "audit-logs",
            "search",
            "--start-date",
            "1700000000000",
            "--end-date",
            "1700100000000",
        ],
    )

    assert result.exit_code == 0
    assert "UPDATE" in result.output
    assert "admin" in result.output
    assert "POLICY" in result.output


def test_search_json_output() -> None:
    _, mock_audit = _stub_client()
    entry = _make_entry()
    paginator = _make_paginator([entry])
    when(mock_audit).search(...).thenReturn(paginator)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "--json",
            "audit-logs",
            "search",
            "--start-date",
            "1700000000000",
            "--end-date",
            "1700100000000",
        ],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["action"] == "UPDATE"
    assert parsed[0]["actor"] == "admin"
    assert parsed[0]["entity_type"] == "POLICY"


def test_search_with_filter_options() -> None:
    _, mock_audit = _stub_client()
    entry = _make_entry(action="CREATE", entity_type="COMPONENT")
    paginator = _make_paginator([entry])
    when(mock_audit).search(...).thenReturn(paginator)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "audit-logs",
            "search",
            "--start-date",
            "1700000000000",
            "--end-date",
            "1700100000000",
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


def test_search_missing_required_dates() -> None:
    _stub_client()

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "audit-logs", "search"],
    )

    assert result.exit_code != 0
    assert (
        "start-date" in result.output.lower() or "start_date" in result.output.lower()
    )
