from __future__ import annotations

from typing import cast

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._dashboard import DashboardService
from nextlabs_sdk._cloudaz._dashboard_models import (
    ActivityByEntity,
    Alert,
    MonitorTagAlert,
    PolicyActivity,
)

BASE_URL = "https://cloudaz.example.com"
_BASE_PATH = "/nextlabs-reporter/api/v1/dashboard"
_START = 1708560000000
_END = 1708646400000
_SOURCE = "AD"


def _make_data_envelope(data: object) -> httpx.Response:
    return httpx.Response(
        200,
        json={"statusCode": "1003", "message": "Data found successfully", "data": data},
        request=httpx.Request("GET", f"{BASE_URL}/api"),
    )


@pytest.fixture
def service() -> tuple[DashboardService, httpx.Client]:
    client = cast(httpx.Client, mock(httpx.Client))
    return DashboardService(client), client


def test_latest_alerts(service: tuple[DashboardService, httpx.Client]) -> None:
    svc, client = service
    raw = [
        {
            "level": "L3",
            "alertMessage": "",
            "monitorName": "Deny Policy",
            "triggeredAt": "2024-02-22T15:55:27.407+00:00",
        },
        {
            "level": "L3",
            "alertMessage": "",
            "monitorName": "Allow Policy",
            "triggeredAt": "2024-02-21T22:20:24.077+00:00",
        },
    ]
    when(client).get(f"{_BASE_PATH}/latestAlerts/{_START}/{_END}").thenReturn(
        _make_data_envelope(raw)
    )

    alerts = svc.latest_alerts(_START, _END)
    assert len(alerts) == 2
    assert isinstance(alerts[0], Alert)
    assert alerts[0].monitor_name == "Deny Policy"
    assert alerts[1].monitor_name == "Allow Policy"


def test_alerts_by_monitor_tags(service: tuple[DashboardService, httpx.Client]) -> None:
    svc, client = service
    raw = [
        {"tagValue": "Weekly Monitoring", "monitorName": "Deny Policy", "alertCount": 1}
    ]
    when(client).get(f"{_BASE_PATH}/alertByMonitorTags/{_START}/{_END}").thenReturn(
        _make_data_envelope(raw)
    )

    tag_alerts = svc.alerts_by_monitor_tags(_START, _END)
    assert len(tag_alerts) == 1
    assert isinstance(tag_alerts[0], MonitorTagAlert)
    assert tag_alerts[0].tag_value == "Weekly Monitoring"
    assert tag_alerts[0].alert_count == 1


def test_top_users(service: tuple[DashboardService, httpx.Client]) -> None:
    svc, client = service
    raw = [
        {
            "name": "John Mason",
            "allowCount": 360,
            "denyCount": 428,
            "decisionCount": 788,
        }
    ]
    when(client).get(
        f"{_BASE_PATH}/activityByUsers/{_START}/{_END}/{_SOURCE}"
    ).thenReturn(_make_data_envelope(raw))

    users = svc.top_users(_START, _END, _SOURCE)
    assert len(users) == 1
    assert isinstance(users[0], ActivityByEntity)
    assert users[0].name == "John Mason"
    assert users[0].allow_count == 360


def test_top_resources(service: tuple[DashboardService, httpx.Client]) -> None:
    svc, client = service
    raw = [
        {
            "name": "sap://ed6/ed6/100/ecc/cv02n/0000000000000010000001317",
            "allowCount": 480,
            "denyCount": 488,
            "decisionCount": 968,
        }
    ]
    when(client).get(
        f"{_BASE_PATH}/activityByResources/{_START}/{_END}/{_SOURCE}"
    ).thenReturn(_make_data_envelope(raw))

    resources = svc.top_resources(_START, _END, _SOURCE)
    assert len(resources) == 1
    assert isinstance(resources[0], ActivityByEntity)
    assert resources[0].decision_count == 968


def test_top_policies(service: tuple[DashboardService, httpx.Client]) -> None:
    svc, client = service
    raw = [
        {
            "policy_decisions": [
                {"day_nb": 1680505200000, "allow_count": 17, "deny_count": 13},
                {"day_nb": 1680591600000, "allow_count": 13, "deny_count": 10},
            ],
            "policy_name": "Deny access to Security Vulnerabilities",
        }
    ]
    when(client).get(
        f"{_BASE_PATH}/activityByPolicies/{_START}/{_END}/{_SOURCE}"
    ).thenReturn(_make_data_envelope(raw))

    policies = svc.top_policies(_START, _END, _SOURCE)
    assert len(policies) == 1
    assert isinstance(policies[0], PolicyActivity)
    assert policies[0].policy_name == "Deny access to Security Vulnerabilities"
    assert len(policies[0].policy_decisions) == 2


def test_latest_alerts_empty_list(
    service: tuple[DashboardService, httpx.Client],
) -> None:
    svc, client = service
    when(client).get(f"{_BASE_PATH}/latestAlerts/1000/2000").thenReturn(
        _make_data_envelope([])
    )

    assert svc.latest_alerts(1000, 2000) == []
