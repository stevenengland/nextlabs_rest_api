from __future__ import annotations

import json
from typing import Any

from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._report_models import (
    EnforcementEntry,
    PolicyActivityReport,
    PolicyActivityReportDetail,
    WidgetData,
)
from nextlabs_sdk._cloudaz._reports import PolicyActivityReportService
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


def _stub_client() -> tuple[Any, Any]:
    mock_client = mock(CloudAzClient)
    mock_reports = mock(PolicyActivityReportService)
    mock_client.reports = mock_reports
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)
    return mock_client, mock_reports


def _make_report(
    report_id: int = 1,
    title: str = "My Report",
) -> PolicyActivityReport:
    return PolicyActivityReport.model_validate(
        {
            "id": report_id,
            "title": title,
            "description": "A test report",
            "sharedMode": "PRIVATE",
            "decision": "AD",
            "dateMode": "RELATIVE",
            "windowMode": "LAST_7_DAYS",
            "startDate": "2024-01-01",
            "endDate": "2024-01-31",
            "lastUpdatedDate": "2024-06-01",
            "type": "POLICY_ACTIVITY",
        }
    )


def _make_report_paginator(
    reports: list[PolicyActivityReport],
) -> SyncPaginator[PolicyActivityReport]:
    page = PageResult(
        entries=reports,
        page_no=0,
        page_size=len(reports),
        total_pages=1,
        total_records=len(reports),
    )

    def fetch_page(page_no: int) -> PageResult[PolicyActivityReport]:
        return page

    return SyncPaginator(fetch_page=fetch_page)


def _make_enforcement(row_id: int = 100) -> EnforcementEntry:
    return EnforcementEntry.model_validate(
        {
            "ROW_ID": row_id,
            "TIME": "2024-06-01 12:00:00",
            "USER_NAME": "admin@test.com",
            "FROM_RESOURCE_NAME": "/shared/docs",
            "POLICY_NAME": "AllowRead",
            "POLICY_DECISION": "Allow",
            "ACTION": "READ",
        }
    )


def _make_enforcement_paginator(
    entries: list[EnforcementEntry],
) -> SyncPaginator[EnforcementEntry]:
    page = PageResult(
        entries=entries,
        page_no=0,
        page_size=len(entries),
        total_pages=1,
        total_records=len(entries),
    )

    def fetch_page(page_no: int) -> PageResult[EnforcementEntry]:
        return page

    return SyncPaginator(fetch_page=fetch_page)


def _make_report_detail() -> PolicyActivityReportDetail:
    return PolicyActivityReportDetail.model_validate(
        {
            "criteria": {"filters": None, "header": ["TIME", "USER_NAME"]},
            "widgets": [
                {
                    "name": "trend",
                    "title": "Trend",
                    "chartType": "LINE",
                    "attributeName": "TIME",
                }
            ],
        }
    )


def _make_widget_data() -> WidgetData:
    return WidgetData.model_validate(
        {
            "enforcements": [
                {
                    "hour": 10,
                    "allowCount": 5,
                    "denyCount": 2,
                    "decisionCount": 7,
                }
            ]
        }
    )


# ── list ──


def test_reports_list_table_output() -> None:
    _, mock_reports = _stub_client()
    report = _make_report()
    paginator = _make_report_paginator([report])
    when(mock_reports).list(
        title="",
        is_shared=True,
        policy_decision="AD",
        sort_by="title",
        sort_order="ascending",
        page_size=20,
    ).thenReturn(paginator)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "reports", "list"])

    assert result.exit_code == 0
    assert "My Report" in result.output
    assert "AD" in result.output


def test_reports_list_json_output() -> None:
    _, mock_reports = _stub_client()
    report = _make_report()
    paginator = _make_report_paginator([report])
    when(mock_reports).list(
        title="",
        is_shared=True,
        policy_decision="AD",
        sort_by="title",
        sort_order="ascending",
        page_size=20,
    ).thenReturn(paginator)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "--json", "reports", "list"])

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["title"] == "My Report"


def test_reports_list_with_options() -> None:
    _, mock_reports = _stub_client()
    report = _make_report()
    paginator = _make_report_paginator([report])
    when(mock_reports).list(
        title="Test",
        is_shared=False,
        policy_decision="A",
        sort_by="id",
        sort_order="descending",
        page_size=10,
    ).thenReturn(paginator)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "reports",
            "list",
            "--title",
            "Test",
            "--no-shared",
            "--decision",
            "A",
            "--sort-by",
            "id",
            "--sort-order",
            "descending",
            "--page-size",
            "10",
        ],
    )

    assert result.exit_code == 0
    assert "My Report" in result.output


# ── get ──


def test_reports_get_json_output() -> None:
    _, mock_reports = _stub_client()
    detail = _make_report_detail()
    when(mock_reports).get(1).thenReturn(detail)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "reports", "get", "1"])

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "criteria" in parsed
    assert "widgets" in parsed


def test_reports_get_not_found() -> None:
    _, mock_reports = _stub_client()
    when(mock_reports).get(999).thenRaise(NotFoundError(message="HTTP 404"))

    result = runner.invoke(app, [*_GLOBAL_OPTS, "reports", "get", "999"])

    assert result.exit_code == 1
    assert "Not found" in result.output


# ── create ──


def test_reports_create_success() -> None:
    _, mock_reports = _stub_client()
    report = _make_report(report_id=42)
    when(mock_reports).create(...).thenReturn(report)

    payload = {
        "criteria": {"filters": None},
        "widgets": [
            {
                "name": "trend",
                "title": "Trend",
                "chartType": "LINE",
                "attributeName": "TIME",
            }
        ],
    }
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "reports", "create", "--data", json.dumps(payload)],
    )

    assert result.exit_code == 0
    assert "42" in result.output


def test_reports_create_invalid_json() -> None:
    _stub_client()

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "reports", "create", "--data", "not-json"],
    )

    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


# ── modify ──


def test_reports_modify_success() -> None:
    _, mock_reports = _stub_client()
    report = _make_report()
    when(mock_reports).modify(...).thenReturn(report)

    payload = {
        "criteria": {"filters": None},
    }
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "reports",
            "modify",
            "1",
            "--data",
            json.dumps(payload),
        ],
    )

    assert result.exit_code == 0
    assert "Modified" in result.output


# ── delete ──


def test_reports_delete_success() -> None:
    _, mock_reports = _stub_client()
    when(mock_reports).delete(...).thenReturn(None)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "reports", "delete", "1", "2", "3"],
    )

    assert result.exit_code == 0
    assert "Deleted" in result.output


# ── widgets ──


def test_reports_widgets_json_output() -> None:
    _, mock_reports = _stub_client()
    widget_data = _make_widget_data()
    when(mock_reports).get_widgets(1).thenReturn(widget_data)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "reports", "widgets", "1"])

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "enforcements" in parsed
    assert parsed["enforcements"][0]["hour"] == 10


# ── enforcements ──


def test_reports_enforcements_table_output() -> None:
    _, mock_reports = _stub_client()
    entry = _make_enforcement()
    paginator = _make_enforcement_paginator([entry])
    when(mock_reports).get_enforcements(
        1,
        sort_by="rowId",
        sort_order="ascending",
        page_size=20,
    ).thenReturn(paginator)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "reports", "enforcements", "1"],
    )

    assert result.exit_code == 0
    assert "AllowRead" in result.output
    assert "Allow" in result.output


def test_reports_enforcements_json_output() -> None:
    _, mock_reports = _stub_client()
    entry = _make_enforcement()
    paginator = _make_enforcement_paginator([entry])
    when(mock_reports).get_enforcements(
        1,
        sort_by="rowId",
        sort_order="ascending",
        page_size=20,
    ).thenReturn(paginator)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--json", "reports", "enforcements", "1"],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["row_id"] == 100


def test_reports_enforcements_with_options() -> None:
    _, mock_reports = _stub_client()
    entry = _make_enforcement()
    paginator = _make_enforcement_paginator([entry])
    when(mock_reports).get_enforcements(
        1,
        sort_by="TIME",
        sort_order="descending",
        page_size=50,
    ).thenReturn(paginator)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "reports",
            "enforcements",
            "1",
            "--sort-by",
            "TIME",
            "--sort-order",
            "descending",
            "--page-size",
            "50",
        ],
    )

    assert result.exit_code == 0
    assert "100" in result.output


# ── export ──


def test_reports_export_writes_bytes() -> None:
    _, mock_reports = _stub_client()
    when(mock_reports).export(
        1,
        sort_by="rowId",
        sort_order="ascending",
    ).thenReturn(b"col1,col2\nval1,val2\n")

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "reports", "export", "1"],
    )

    assert result.exit_code == 0
    assert "col1,col2" in result.output


def test_reports_export_with_options() -> None:
    _, mock_reports = _stub_client()
    when(mock_reports).export(
        1,
        sort_by="TIME",
        sort_order="descending",
    ).thenReturn(b"exported\n")

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "reports",
            "export",
            "1",
            "--sort-by",
            "TIME",
            "--sort-order",
            "descending",
        ],
    )

    assert result.exit_code == 0
    assert "exported" in result.output
