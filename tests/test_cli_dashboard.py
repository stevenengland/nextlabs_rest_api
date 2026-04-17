from __future__ import annotations

import json
from typing import Any

import pytest
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
        },
    )


def _make_activity(name: str = "admin_user") -> ActivityByEntity:
    return ActivityByEntity.model_validate(
        {"name": name, "allowCount": 100, "denyCount": 5, "decisionCount": 105},
    )


def _make_policy_activity() -> PolicyActivity:
    return PolicyActivity(
        policy_name="Access Control Policy",
        policy_decisions=[
            PolicyDayBucket(day_nb=1, allow_count=50, deny_count=3),
            PolicyDayBucket(day_nb=2, allow_count=45, deny_count=7),
        ],
    )


def _invoke(command: str, *, json_flag: bool, extra: tuple[str, ...] = ()) -> Any:
    prefix = (
        *_GLOBAL_OPTS,
        *(
            (
                "--output",
                "json",
            )
            if json_flag
            else ()
        ),
        "dashboard",
        command,
        *_DATE_OPTS,
        *extra,
    )
    return runner.invoke(app, list(prefix))


@pytest.mark.parametrize(
    "command,service_method,factory,table_checks,json_checks",
    [
        pytest.param(
            "alerts",
            "latest_alerts",
            _make_alert,
            ["CRITICAL", "CPU usage exceeded 90%", "System Monitor"],
            {"level": "CRITICAL", "alert_message": "CPU usage exceeded 90%"},
            id="alerts",
        ),
        pytest.param(
            "top-users",
            "top_users",
            _make_activity,
            ["admin_user", "100", "105"],
            {"name": "admin_user", "allow_count": 100},
            id="top-users",
        ),
        pytest.param(
            "top-resources",
            "top_resources",
            lambda: _make_activity(name="SharePoint"),
            ["SharePoint", "100"],
            {"name": "SharePoint"},
            id="top-resources",
        ),
    ],
)
@pytest.mark.parametrize("json_flag", [False, True], ids=["table", "json"])
def test_dashboard_command_output(
    command, service_method, factory, table_checks, json_checks, json_flag
):
    _, mock_dashboard = _stub_client()
    getattr(when(mock_dashboard), service_method)(...).thenReturn([factory()])

    result = _invoke(command, json_flag=json_flag)

    assert result.exit_code == 0
    if json_flag:
        parsed = json.loads(result.output)
        assert isinstance(parsed, list)
        for key, value in json_checks.items():
            assert parsed[0][key] == value
    else:
        for fragment in table_checks:
            assert fragment in result.output


def test_alerts_missing_dates():
    _stub_client()

    result = runner.invoke(app, [*_GLOBAL_OPTS, "dashboard", "alerts"])

    assert result.exit_code != 0
    assert "from-date" in result.output.lower() or "from_date" in result.output.lower()


def test_top_users_custom_decision():
    _, mock_dashboard = _stub_client()
    when(mock_dashboard).top_users(...).thenReturn([_make_activity()])

    result = _invoke("top-users", json_flag=False, extra=("--decision", "A"))

    assert result.exit_code == 0
    assert "admin_user" in result.output


def test_top_policies_json_format():
    _, mock_dashboard = _stub_client()
    when(mock_dashboard).top_policies(...).thenReturn([_make_policy_activity()])

    result = _invoke("top-policies", json_flag=False)

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["policy_name"] == "Access Control Policy"
    assert len(parsed[0]["policy_decisions"]) == 2


def test_top_policies_custom_decision():
    _, mock_dashboard = _stub_client()
    when(mock_dashboard).top_policies(...).thenReturn([_make_policy_activity()])

    result = _invoke("top-policies", json_flag=False, extra=("--decision", "D"))

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["policy_name"] == "Access Control Policy"
