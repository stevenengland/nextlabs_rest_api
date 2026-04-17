from __future__ import annotations

import io

from rich.console import Console

from nextlabs_sdk._cli import _reports_cmd
from nextlabs_sdk._cli._detail_renderers import render_detail
from nextlabs_sdk._cloudaz._report_models import (
    PolicyActivityReportDetail,
    WidgetData,
)


def _console() -> tuple[Console, io.StringIO]:
    buf = io.StringIO()
    return Console(file=buf, force_terminal=False, width=120, color_system=None), buf


def test_report_detail_renderer_registered_and_renders_fields() -> None:
    assert _reports_cmd.reports_app is not None
    detail = PolicyActivityReportDetail.model_validate(
        {
            "criteria": {
                "filters": None,
                "header": ["TIME", "USER_NAME"],
                "pagesize": 50,
            },
            "widgets": [
                {
                    "name": "trend",
                    "title": "Trend",
                    "chartType": "LINE",
                    "attributeName": "TIME",
                },
                {
                    "name": "top_users",
                    "title": "Top Users",
                    "chartType": "BAR",
                    "attributeName": "USER_NAME",
                },
            ],
        },
    )
    console, buf = _console()
    render_detail(detail, console=console)
    output = buf.getvalue()
    assert "Report" in output
    assert "Widgets" in output
    assert "2" in output
    assert "trend" in output
    assert "top_users" in output


def test_widget_data_detail_renderer_registered_and_renders_fields() -> None:
    assert _reports_cmd.reports_app is not None
    widget_data = WidgetData.model_validate(
        {
            "enforcements": [
                {"hour": 10, "allowCount": 5, "denyCount": 2, "decisionCount": 7},
                {"hour": 11, "allowCount": 3, "denyCount": 1, "decisionCount": 4},
            ],
        },
    )
    console, buf = _console()
    render_detail(widget_data, console=console)
    output = buf.getvalue()
    assert "WidgetData" in output or "Widget" in output
    assert "Enforcements" in output
    assert "2" in output
