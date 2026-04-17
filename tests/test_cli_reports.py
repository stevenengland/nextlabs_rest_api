from __future__ import annotations

import json
from typing import Any

import pytest
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


@pytest.fixture
def mock_reports() -> Any:
    mock_client = mock(CloudAzClient)
    reports = mock(PolicyActivityReportService)
    mock_client.reports = reports
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)
    return reports


def _make_report(report_id: int = 1, title: str = "My Report") -> PolicyActivityReport:
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
        },
    )


def _paginator(entries: list[Any]) -> SyncPaginator[Any]:
    page = PageResult(
        entries=entries,
        page_no=0,
        page_size=len(entries),
        total_pages=1,
        total_records=len(entries),
    )

    def fetch_page(page_no: int) -> PageResult[Any]:
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
        },
    )


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
                },
            ],
        },
    )


def _make_widget_data() -> WidgetData:
    return WidgetData.model_validate(
        {
            "enforcements": [
                {"hour": 10, "allowCount": 5, "denyCount": 2, "decisionCount": 7},
            ],
        },
    )


def _invoke(json_mode: bool, tail: list[str]) -> Any:
    args = list(_GLOBAL_OPTS)
    if json_mode:
        args.extend(["--output", "json"])
    args.extend(tail)
    return runner.invoke(app, args)


# ── list ──


def _default_list_kw() -> dict[str, Any]:
    return {
        "title": "",
        "is_shared": True,
        "policy_decision": "AD",
        "sort_by": "title",
        "sort_order": "ascending",
        "page_size": 20,
    }


@pytest.mark.parametrize(
    "extra_opts,json_mode,list_kw,check",
    [
        pytest.param(
            [],
            False,
            _default_list_kw(),
            lambda out: "My Report" in out and "AD" in out,
            id="table-default",
        ),
        pytest.param(
            [],
            True,
            _default_list_kw(),
            lambda out: json.loads(out)[0]["title"] == "My Report",
            id="json-default",
        ),
        pytest.param(
            [
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
            False,
            {
                "title": "Test",
                "is_shared": False,
                "policy_decision": "A",
                "sort_by": "id",
                "sort_order": "descending",
                "page_size": 10,
            },
            lambda out: "My Report" in out,
            id="with-options",
        ),
    ],
)
def test_reports_list(
    mock_reports: Any,
    extra_opts: list[str],
    json_mode: bool,
    list_kw: dict[str, Any],
    check: Any,
):
    when(mock_reports).list(**list_kw).thenReturn(_paginator([_make_report()]))

    result = _invoke(json_mode, ["reports", "list", *extra_opts])

    assert result.exit_code == 0
    assert check(result.output)


# ── get ──


def test_reports_get_json_format(mock_reports: Any):
    when(mock_reports).get(1).thenReturn(_make_report_detail())

    result = runner.invoke(app, [*_GLOBAL_OPTS, "reports", "get", "1"])

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "criteria" in parsed
    assert "widgets" in parsed


def test_reports_get_not_found(mock_reports: Any):
    when(mock_reports).get(999).thenRaise(NotFoundError(message="HTTP 404"))

    result = runner.invoke(app, [*_GLOBAL_OPTS, "reports", "get", "999"])

    assert result.exit_code == 1
    assert "Not found" in result.output


# ── create ──


def test_reports_create_success(mock_reports: Any):
    when(mock_reports).create(...).thenReturn(_make_report(report_id=42))
    payload = {
        "criteria": {"filters": None},
        "widgets": [
            {
                "name": "trend",
                "title": "Trend",
                "chartType": "LINE",
                "attributeName": "TIME",
            },
        ],
    }

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "reports", "create", "--data", json.dumps(payload)],
    )

    assert result.exit_code == 0
    assert "42" in result.output


def test_reports_create_invalid_json(mock_reports: Any):
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "reports", "create", "--data", "not-json"],
    )

    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


# ── modify ──


def test_reports_modify_success(mock_reports: Any):
    when(mock_reports).modify(...).thenReturn(_make_report())

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "reports",
            "modify",
            "1",
            "--data",
            json.dumps({"criteria": {"filters": None}}),
        ],
    )

    assert result.exit_code == 0
    assert "Modified" in result.output


# ── delete ──


def test_reports_delete_success(mock_reports: Any):
    when(mock_reports).delete(...).thenReturn(None)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "reports", "delete", "1", "2", "3"])

    assert result.exit_code == 0
    assert "Deleted" in result.output


# ── widgets ──


def test_reports_widgets_json_format(mock_reports: Any):
    when(mock_reports).get_widgets(1).thenReturn(_make_widget_data())

    result = runner.invoke(app, [*_GLOBAL_OPTS, "reports", "widgets", "1"])

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "enforcements" in parsed
    assert parsed["enforcements"][0]["hour"] == 10


# ── enforcements ──


def _default_enf_kw() -> dict[str, Any]:
    return {
        "sort_by": "rowId",
        "sort_order": "ascending",
        "page_size": 20,
    }


@pytest.mark.parametrize(
    "extra_opts,json_mode,enf_kw,check",
    [
        pytest.param(
            [],
            False,
            _default_enf_kw(),
            lambda out: "AllowRead" in out and "Allow" in out,
            id="table-default",
        ),
        pytest.param(
            [],
            True,
            _default_enf_kw(),
            lambda out: json.loads(out)[0]["row_id"] == 100,
            id="json-default",
        ),
        pytest.param(
            [
                "--sort-by",
                "TIME",
                "--sort-order",
                "descending",
                "--page-size",
                "50",
            ],
            False,
            {"sort_by": "TIME", "sort_order": "descending", "page_size": 50},
            lambda out: "100" in out,
            id="with-options",
        ),
    ],
)
def test_reports_enforcements(
    mock_reports: Any,
    extra_opts: list[str],
    json_mode: bool,
    enf_kw: dict[str, Any],
    check: Any,
):
    when(mock_reports).get_enforcements(1, **enf_kw).thenReturn(
        _paginator([_make_enforcement()]),
    )

    result = _invoke(json_mode, ["reports", "enforcements", "1", *extra_opts])

    assert result.exit_code == 0
    assert check(result.output)


# ── export ──


@pytest.mark.parametrize(
    "extra_opts,export_kw,body,expected_text",
    [
        pytest.param(
            [],
            {"sort_by": "rowId", "sort_order": "ascending"},
            b"col1,col2\nval1,val2\n",
            "col1,col2",
            id="default",
        ),
        pytest.param(
            ["--sort-by", "TIME", "--sort-order", "descending"],
            {"sort_by": "TIME", "sort_order": "descending"},
            b"exported\n",
            "exported",
            id="with-options",
        ),
    ],
)
def test_reports_export(
    mock_reports: Any,
    extra_opts: list[str],
    export_kw: dict[str, Any],
    body: bytes,
    expected_text: str,
):
    when(mock_reports).export(1, **export_kw).thenReturn(body)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "reports", "export", "1", *extra_opts],
    )

    assert result.exit_code == 0
    assert expected_text in result.output
