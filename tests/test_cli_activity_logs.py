from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cloudaz._activity_log_query_models import (
    ActivityLogAttribute,
    ActivityLogQuery,
)
from nextlabs_sdk._cloudaz._activity_logs_service import ReportActivityLogService
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._report_models import EnforcementEntry
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
    mock_service = mock(ReportActivityLogService)
    mock_client.activity_logs = mock_service
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)
    return mock_client, mock_service


@pytest.fixture
def query_file(tmp_path: Path) -> Path:
    path = tmp_path / "query.json"
    path.write_text(
        json.dumps(
            {
                "from_date": 1_700_000_000,
                "to_date": 1_700_001_000,
                "policy_decision": "AD",
                "sort_by": "TIME",
                "sort_order": "descending",
                "field_name": "user_name",
                "field_value": "alice",
            },
        ),
    )
    return path


def _entry() -> EnforcementEntry:
    return EnforcementEntry(
        ROW_ID=99,
        TIME="2024-01-01T00:00:00Z",
        USER_NAME="alice",
        POLICY_NAME="Allow",
        POLICY_DECISION="ALLOW",
        ACTION="read",
    )


def _paginator() -> SyncPaginator[EnforcementEntry]:
    def fetch(page_no: int) -> PageResult[EnforcementEntry]:
        return PageResult(
            entries=[_entry()],
            page_no=page_no,
            page_size=1,
            total_pages=1,
            total_records=1,
        )

    return SyncPaginator(fetch_page=fetch)


def test_activity_logs_search_passes_query(
    stub: tuple[Any, Any],
    query_file: Path,
) -> None:
    _, service = stub
    captured: dict[str, Any] = {}

    def _fake(
        query: ActivityLogQuery, *, page_size: int
    ) -> SyncPaginator[EnforcementEntry]:
        captured["query"] = query
        captured["page_size"] = page_size
        return _paginator()

    when(service).search(...).thenAnswer(_fake)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "activity-logs", "search", "--query", str(query_file)],
    )

    assert result.exit_code == 0, result.output
    assert "alice" in result.output
    assert captured["query"].from_date == 1_700_000_000
    assert captured["query"].policy_decision == "AD"
    assert captured["page_size"] == 20


def test_activity_logs_search_json(
    stub: tuple[Any, Any],
    query_file: Path,
) -> None:
    _, service = stub
    when(service).search(...).thenReturn(_paginator())

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "-o",
            "json",
            "activity-logs",
            "search",
            "--query",
            str(query_file),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload[0]["user_name"] == "alice"


def test_activity_logs_get_by_row_id_table(stub: tuple[Any, Any]) -> None:
    _, service = stub
    when(service).get_by_row_id(99).thenReturn(
        [
            ActivityLogAttribute(
                name="USER_NAME",
                value="alice",
                data_type="string",
                attr_type="USER",
                is_dynamic=False,
            ),
        ],
    )

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "activity-logs", "get-by-row-id", "99"],
    )

    assert result.exit_code == 0
    assert "USER_NAME" in result.output
    assert "alice" in result.output


def test_activity_logs_search_wide_includes_extra_columns(
    stub: tuple[Any, Any],
    query_file: Path,
) -> None:
    _, service = stub
    entry = EnforcementEntry(
        ROW_ID=99,
        TIME="2024-01-01T00:00:00Z",
        USER_NAME="alice",
        FROM_RESOURCE_NAME="source.txt",
        FROM_RESOURCE_PATH="/data/source.txt",
        TO_RESOURCE_NAME="dest.txt",
        POLICY_NAME="Allow",
        POLICY_DECISION="ALLOW",
        ACTION="read",
        ACTION_SHORT_CODE="R",
        LOG_LEVEL="INFO",
    )

    def fetch(page_no: int) -> PageResult[EnforcementEntry]:
        return PageResult(
            entries=[entry],
            page_no=page_no,
            page_size=1,
            total_pages=1,
            total_records=1,
        )

    when(service).search(...).thenReturn(SyncPaginator(fetch_page=fetch))

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "--output",
            "wide",
            "activity-logs",
            "search",
            "--query",
            str(query_file),
        ],
        env={"COLUMNS": "320"},
    )

    assert result.exit_code == 0, result.output
    output = result.output.replace("\n", " ")
    assert "Resource" in output
    assert "From Resource Path" in output
    assert "To Resource" in output
    assert "Short Code" in output
    assert "Log Level" in output
    assert "/data/source.txt" in output
    assert "dest.txt" in output
    assert "INFO" in output


def test_activity_logs_export_writes_bytes(
    stub: tuple[Any, Any],
    tmp_path: Path,
    query_file: Path,
) -> None:
    _, service = stub
    when(service).export(...).thenReturn(b"csv,data")

    out = tmp_path / "export.csv"
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "activity-logs",
            "export",
            "--query",
            str(query_file),
            "--output",
            str(out),
        ],
    )

    assert result.exit_code == 0, result.output
    assert out.read_bytes() == b"csv,data"


def test_activity_logs_export_requires_output(
    stub: tuple[Any, Any],
    query_file: Path,
) -> None:
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "activity-logs", "export", "--query", str(query_file)],
    )

    assert result.exit_code != 0


def test_activity_logs_export_by_row_id(
    stub: tuple[Any, Any],
    tmp_path: Path,
) -> None:
    _, service = stub
    when(service).export_by_row_id(99).thenReturn(b"row-bytes")

    out = tmp_path / "row.bin"
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "activity-logs",
            "export-by-row-id",
            "99",
            "--output",
            str(out),
        ],
    )

    assert result.exit_code == 0
    assert out.read_bytes() == b"row-bytes"


def test_activity_logs_search_error(
    stub: tuple[Any, Any],
    query_file: Path,
) -> None:
    _, service = stub
    when(service).search(...).thenRaise(NextLabsError("boom"))

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "activity-logs", "search", "--query", str(query_file)],
    )

    assert result.exit_code == 1
    assert "boom" in result.output


def test_activity_logs_search_invalid_query(
    stub: tuple[Any, Any],
    tmp_path: Path,
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"from_date": 1}))

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "activity-logs", "search", "--query", str(bad)],
    )

    assert result.exit_code == 1
    assert "Invalid activity log query" in result.output


def test_activity_logs_search_inline_flags_only(
    stub: tuple[Any, Any],
) -> None:
    _, service = stub
    captured: dict[str, Any] = {}

    def _fake(
        query: ActivityLogQuery, *, page_size: int
    ) -> SyncPaginator[EnforcementEntry]:
        captured["query"] = query
        return _paginator()

    when(service).search(...).thenAnswer(_fake)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "activity-logs",
            "search",
            "--field-name",
            "user_name",
            "--field-value",
            "alice",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["query"].field_name == "user_name"
    assert captured["query"].field_value == "alice"
    assert captured["query"].policy_decision == "AD"
    assert captured["query"].sort_by == "time"
    assert captured["query"].sort_order == "descending"


def test_activity_logs_search_flag_overrides_file(
    stub: tuple[Any, Any],
    query_file: Path,
) -> None:
    _, service = stub
    captured: dict[str, Any] = {}

    def _fake(
        query: ActivityLogQuery, *, page_size: int
    ) -> SyncPaginator[EnforcementEntry]:
        captured["query"] = query
        return _paginator()

    when(service).search(...).thenAnswer(_fake)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "activity-logs",
            "search",
            "--query",
            str(query_file),
            "--field-value",
            "carol",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["query"].field_value == "carol"
    assert captured["query"].field_name == "user_name"
    assert captured["query"].from_date == 1_700_000_000


def test_activity_logs_search_headers_repeatable(
    stub: tuple[Any, Any],
) -> None:
    _, service = stub
    captured: dict[str, Any] = {}

    def _fake(
        query: ActivityLogQuery, *, page_size: int
    ) -> SyncPaginator[EnforcementEntry]:
        captured["query"] = query
        return _paginator()

    when(service).search(...).thenAnswer(_fake)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "activity-logs",
            "search",
            "--field-name",
            "u",
            "--field-value",
            "v",
            "--header",
            "a",
            "--header",
            "b",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["query"].header == ["a", "b"]


def test_activity_logs_search_from_date_epoch_ms(
    stub: tuple[Any, Any],
) -> None:
    _, service = stub
    captured: dict[str, Any] = {}

    def _fake(
        query: ActivityLogQuery, *, page_size: int
    ) -> SyncPaginator[EnforcementEntry]:
        captured["query"] = query
        return _paginator()

    when(service).search(...).thenAnswer(_fake)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "activity-logs",
            "search",
            "--field-name",
            "u",
            "--field-value",
            "v",
            "--from-date",
            "1737014400000",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["query"].from_date == 1_737_014_400_000


def test_activity_logs_search_inline_missing_required_errors(
    stub: tuple[Any, Any],
) -> None:
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "activity-logs", "search"],
    )

    assert result.exit_code == 1
    assert "Missing required option" in result.output
    assert "--field-name" in result.output
    assert "--field-value" in result.output
    assert "validation error" not in result.output.lower()


def test_activity_logs_search_inline_defaults_to_date_and_header(
    stub: tuple[Any, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nextlabs_sdk._cli import _activity_log_query_builder as builder_mod

    monkeypatch.setattr(builder_mod, "now_epoch_ms", lambda: 9_999_000)

    _, service = stub
    captured: dict[str, Any] = {}

    def _fake(
        query: ActivityLogQuery, *, page_size: int
    ) -> SyncPaginator[EnforcementEntry]:
        captured["query"] = query
        return _paginator()

    when(service).search(...).thenAnswer(_fake)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "activity-logs",
            "search",
            "--field-name",
            "u",
            "--field-value",
            "v",
            "--from-date",
            "1737014400000",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["query"].to_date == 9_999_000
    assert captured["query"].header == [
        "ROW_ID",
        "TIME",
        "USER_NAME",
        "FROM_RESOURCE_NAME",
        "POLICY_NAME",
        "POLICY_DECISION",
        "ACTION",
    ]


def test_activity_logs_export_inline_defaults_to_date_and_header(
    stub: tuple[Any, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nextlabs_sdk._cli import _activity_log_query_builder as builder_mod

    monkeypatch.setattr(builder_mod, "now_epoch_ms", lambda: 7_777_000)

    _, service = stub
    captured: dict[str, Any] = {}

    def _fake(query: ActivityLogQuery) -> bytes:
        captured["query"] = query
        return b"csv"

    when(service).export(...).thenAnswer(_fake)

    out = tmp_path / "export.csv"
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "activity-logs",
            "export",
            "--output",
            str(out),
            "--field-name",
            "u",
            "--field-value",
            "v",
            "--from-date",
            "1737014400000",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["query"].to_date == 7_777_000
    assert "ROW_ID" in captured["query"].header


def test_activity_logs_search_file_mode_does_not_inject_defaults(
    stub: tuple[Any, Any],
    query_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nextlabs_sdk._cli import _activity_log_query_builder as builder_mod

    monkeypatch.setattr(builder_mod, "now_epoch_ms", lambda: 9_999_000)

    _, service = stub
    captured: dict[str, Any] = {}

    def _fake(
        query: ActivityLogQuery, *, page_size: int
    ) -> SyncPaginator[EnforcementEntry]:
        captured["query"] = query
        return _paginator()

    when(service).search(...).thenAnswer(_fake)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "activity-logs", "search", "--query", str(query_file)],
    )

    assert result.exit_code == 0, result.output
    assert captured["query"].header is None


def test_activity_logs_export_inline_missing_required_errors(
    stub: tuple[Any, Any],
    tmp_path: Path,
) -> None:
    out = tmp_path / "export.csv"
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "activity-logs", "export", "--output", str(out)],
    )

    assert result.exit_code == 1
    assert "Missing required option" in result.output
    assert "--field-name" in result.output
    assert "--field-value" in result.output


def test_activity_logs_export_inline_flags_only(
    stub: tuple[Any, Any],
    tmp_path: Path,
) -> None:
    _, service = stub
    captured: dict[str, Any] = {}

    def _fake(query: ActivityLogQuery) -> bytes:
        captured["query"] = query
        return b"csv"

    when(service).export(...).thenAnswer(_fake)

    out = tmp_path / "export.csv"
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "activity-logs",
            "export",
            "--output",
            str(out),
            "--field-name",
            "u",
            "--field-value",
            "v",
        ],
    )

    assert result.exit_code == 0, result.output
    assert out.read_bytes() == b"csv"
    assert captured["query"].field_name == "u"
    assert captured["query"].policy_decision == "AD"
