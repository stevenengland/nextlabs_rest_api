from __future__ import annotations

import json
from typing import Any

from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._dashboard import DashboardService
from nextlabs_sdk._cloudaz._dashboard_models import (
    ActivityByEntity,
    Alert,
    PolicyActivity,
    PolicyDayBucket,
)

runner = CliRunner()

_GLOBAL_OPTS = (
    "--base-url",
    "https://example.com",
    "--username",
    "admin",
    "--password",
    "secret",
)

_DATE_OPTS = ("--from-date", "1713264000000", "--to-date", "1713350400000")


def _stub_client() -> tuple[Any, Any]:
    mock_client = mock(CloudAzClient)
    mock_dashboard = mock(DashboardService)
    mock_client.dashboard = mock_dashboard
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)
    return mock_client, mock_dashboard


def _make_alert() -> Alert:
    return Alert.model_validate(
        {
            "level": "CRITICAL",
            "alertMessage": "CPU usage exceeded 90%",
            "monitorName": "System Monitor",
            "triggeredAt": "2024-04-16T12:00:00Z",
        }
    )


def _make_activity(name: str = "admin_user") -> ActivityByEntity:
    return ActivityByEntity.model_validate(
        {
            "name": name,
            "allowCount": 100,
            "denyCount": 5,
            "decisionCount": 105,
        }
    )


def _make_policy_activity() -> PolicyActivity:
    return PolicyActivity(
        policy_name="Access Control Policy",
        policy_decisions=[
            PolicyDayBucket(day_nb=1, allow_count=50, deny_count=3),
            PolicyDayBucket(day_nb=2, allow_count=45, deny_count=7),
        ],
    )


# --- alerts ---


def test_alerts_table_output() -> None:
    _, mock_dashboard = _stub_client()
    alert = _make_alert()
    when(mock_dashboard).latest_alerts(...).thenReturn([alert])

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "dashboard", "alerts", *_DATE_OPTS],
    )

    assert result.exit_code == 0
    assert "CRITICAL" in result.output
    assert "CPU usage exceeded 90%" in result.output
    assert "System Monitor" in result.output


def test_alerts_json_output() -> None:
    _, mock_dashboard = _stub_client()
    alert = _make_alert()
    when(mock_dashboard).latest_alerts(...).thenReturn([alert])

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--json", "dashboard", "alerts", *_DATE_OPTS],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["level"] == "CRITICAL"
    assert parsed[0]["alert_message"] == "CPU usage exceeded 90%"


def test_alerts_missing_dates() -> None:
    _stub_client()

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "dashboard", "alerts"],
    )

    assert result.exit_code != 0
    assert "from-date" in result.output.lower() or "from_date" in result.output.lower()


# --- top-users ---


def test_top_users_table_output() -> None:
    _, mock_dashboard = _stub_client()
    activity = _make_activity()
    when(mock_dashboard).top_users(...).thenReturn([activity])

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "dashboard", "top-users", *_DATE_OPTS],
    )

    assert result.exit_code == 0
    assert "admin_user" in result.output
    assert "100" in result.output
    assert "105" in result.output


def test_top_users_json_output() -> None:
    _, mock_dashboard = _stub_client()
    activity = _make_activity()
    when(mock_dashboard).top_users(...).thenReturn([activity])

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--json", "dashboard", "top-users", *_DATE_OPTS],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["name"] == "admin_user"
    assert parsed[0]["allow_count"] == 100


def test_top_users_custom_decision() -> None:
    _, mock_dashboard = _stub_client()
    activity = _make_activity()
    when(mock_dashboard).top_users(...).thenReturn([activity])

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "dashboard",
            "top-users",
            *_DATE_OPTS,
            "--decision",
            "A",
        ],
    )

    assert result.exit_code == 0
    assert "admin_user" in result.output


# --- top-resources ---


def test_top_resources_table_output() -> None:
    _, mock_dashboard = _stub_client()
    activity = _make_activity(name="SharePoint")
    when(mock_dashboard).top_resources(...).thenReturn([activity])

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "dashboard", "top-resources", *_DATE_OPTS],
    )

    assert result.exit_code == 0
    assert "SharePoint" in result.output
    assert "100" in result.output


def test_top_resources_json_output() -> None:
    _, mock_dashboard = _stub_client()
    activity = _make_activity(name="SharePoint")
    when(mock_dashboard).top_resources(...).thenReturn([activity])

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--json", "dashboard", "top-resources", *_DATE_OPTS],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["name"] == "SharePoint"


# --- top-policies ---


def test_top_policies_json_output() -> None:
    _, mock_dashboard = _stub_client()
    policy = _make_policy_activity()
    when(mock_dashboard).top_policies(...).thenReturn([policy])

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "dashboard", "top-policies", *_DATE_OPTS],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["policy_name"] == "Access Control Policy"
    assert len(parsed[0]["policy_decisions"]) == 2


def test_top_policies_custom_decision() -> None:
    _, mock_dashboard = _stub_client()
    policy = _make_policy_activity()
    when(mock_dashboard).top_policies(...).thenReturn([policy])

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "dashboard",
            "top-policies",
            *_DATE_OPTS,
            "--decision",
            "D",
        ],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["policy_name"] == "Access Control Policy"
