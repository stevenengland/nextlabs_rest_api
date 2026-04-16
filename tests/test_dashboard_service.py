from __future__ import annotations

import httpx
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


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_data_envelope(data: object) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": data,
        },
        request=_make_request(),
    )


def test_latest_alerts() -> None:
    client = mock(httpx.Client)
    service = DashboardService(client)

    raw_alerts = [
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
    response = _make_data_envelope(raw_alerts)
    when(client).get(
        f"{_BASE_PATH}/latestAlerts/1708560000000/1708646400000"
    ).thenReturn(response)

    alerts = service.latest_alerts(1708560000000, 1708646400000)
    assert len(alerts) == 2
    assert isinstance(alerts[0], Alert)
    assert alerts[0].monitor_name == "Deny Policy"
    assert alerts[1].monitor_name == "Allow Policy"


def test_alerts_by_monitor_tags() -> None:
    client = mock(httpx.Client)
    service = DashboardService(client)

    raw = [
        {
            "tagValue": "Weekly Monitoring",
            "monitorName": "Deny Policy",
            "alertCount": 1,
        },
    ]
    response = _make_data_envelope(raw)
    when(client).get(
        f"{_BASE_PATH}/alertByMonitorTags/1708560000000/1708646400000"
    ).thenReturn(response)

    tag_alerts = service.alerts_by_monitor_tags(1708560000000, 1708646400000)
    assert len(tag_alerts) == 1
    assert isinstance(tag_alerts[0], MonitorTagAlert)
    assert tag_alerts[0].tag_value == "Weekly Monitoring"
    assert tag_alerts[0].alert_count == 1


def test_top_users() -> None:
    client = mock(httpx.Client)
    service = DashboardService(client)

    raw = [
        {
            "name": "John Mason",
            "allowCount": 360,
            "denyCount": 428,
            "decisionCount": 788,
        },
    ]
    response = _make_data_envelope(raw)
    when(client).get(
        f"{_BASE_PATH}/activityByUsers/1708560000000/1708646400000/AD"
    ).thenReturn(response)

    users = service.top_users(1708560000000, 1708646400000, "AD")
    assert len(users) == 1
    assert isinstance(users[0], ActivityByEntity)
    assert users[0].name == "John Mason"
    assert users[0].allow_count == 360


def test_top_resources() -> None:
    client = mock(httpx.Client)
    service = DashboardService(client)

    raw = [
        {
            "name": "sap://ed6/ed6/100/ecc/cv02n/0000000000000010000001317",
            "allowCount": 480,
            "denyCount": 488,
            "decisionCount": 968,
        },
    ]
    response = _make_data_envelope(raw)
    when(client).get(
        f"{_BASE_PATH}/activityByResources/1708560000000/1708646400000/AD"
    ).thenReturn(response)

    resources = service.top_resources(1708560000000, 1708646400000, "AD")
    assert len(resources) == 1
    assert isinstance(resources[0], ActivityByEntity)
    assert resources[0].decision_count == 968


def test_top_policies() -> None:
    client = mock(httpx.Client)
    service = DashboardService(client)

    raw = [
        {
            "policy_decisions": [
                {"day_nb": 1680505200000, "allow_count": 17, "deny_count": 13},
                {"day_nb": 1680591600000, "allow_count": 13, "deny_count": 10},
            ],
            "policy_name": "Deny access to Security Vulnerabilities",
        },
    ]
    response = _make_data_envelope(raw)
    when(client).get(
        f"{_BASE_PATH}/activityByPolicies/1708560000000/1708646400000/AD"
    ).thenReturn(response)

    policies = service.top_policies(1708560000000, 1708646400000, "AD")
    assert len(policies) == 1
    assert isinstance(policies[0], PolicyActivity)
    assert policies[0].policy_name == "Deny access to Security Vulnerabilities"
    assert len(policies[0].policy_decisions) == 2


def test_latest_alerts_empty_list() -> None:
    client = mock(httpx.Client)
    service = DashboardService(client)

    response = _make_data_envelope([])
    when(client).get(f"{_BASE_PATH}/latestAlerts/1000/2000").thenReturn(response)

    alerts = service.latest_alerts(1000, 2000)
    assert alerts == []
