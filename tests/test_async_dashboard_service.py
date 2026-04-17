from __future__ import annotations

import asyncio
from typing import Any, Callable

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._dashboard import AsyncDashboardService
from nextlabs_sdk._cloudaz._dashboard_models import (
    ActivityByEntity,
    Alert,
    MonitorTagAlert,
    PolicyActivity,
)

BASE_URL = "https://cloudaz.example.com"
_BASE_PATH = "/nextlabs-reporter/api/v1/dashboard"
_FROM = 1708560000000
_TO = 1708646400000


def _data_envelope(data: object) -> httpx.Response:
    return httpx.Response(
        200,
        json={"statusCode": "1003", "message": "Data found successfully", "data": data},
        request=httpx.Request("GET", f"{BASE_URL}/api"),
    )


@pytest.mark.parametrize(
    "url_suffix,raw,method_call,expected_type,extra_assert",
    [
        pytest.param(
            f"/latestAlerts/{_FROM}/{_TO}",
            [
                {
                    "level": "L3",
                    "alertMessage": "",
                    "monitorName": "Deny Policy",
                    "triggeredAt": "2024-02-22T15:55:27.407+00:00",
                },
            ],
            lambda svc: svc.latest_alerts(_FROM, _TO),
            Alert,
            lambda items: items[0].monitor_name == "Deny Policy",
            id="latest-alerts",
        ),
        pytest.param(
            f"/alertByMonitorTags/{_FROM}/{_TO}",
            [
                {
                    "tagValue": "Weekly Monitoring",
                    "monitorName": "Deny Policy",
                    "alertCount": 1,
                },
            ],
            lambda svc: svc.alerts_by_monitor_tags(_FROM, _TO),
            MonitorTagAlert,
            lambda items: True,
            id="alerts-by-monitor-tags",
        ),
        pytest.param(
            f"/activityByUsers/{_FROM}/{_TO}/AD",
            [
                {
                    "name": "John Mason",
                    "allowCount": 360,
                    "denyCount": 428,
                    "decisionCount": 788,
                },
            ],
            lambda svc: svc.top_users(_FROM, _TO, "AD"),
            ActivityByEntity,
            lambda items: items[0].name == "John Mason",
            id="top-users",
        ),
        pytest.param(
            f"/activityByResources/{_FROM}/{_TO}/AD",
            [
                {
                    "name": "sap://resource/1",
                    "allowCount": 480,
                    "denyCount": 488,
                    "decisionCount": 968,
                },
            ],
            lambda svc: svc.top_resources(_FROM, _TO, "AD"),
            ActivityByEntity,
            lambda items: items[0].decision_count == 968,
            id="top-resources",
        ),
        pytest.param(
            f"/activityByPolicies/{_FROM}/{_TO}/AD",
            [
                {
                    "policy_decisions": [
                        {
                            "day_nb": 1680505200000,
                            "allow_count": 17,
                            "deny_count": 13,
                        },
                    ],
                    "policy_name": "Deny access to Security Vulnerabilities",
                },
            ],
            lambda svc: svc.top_policies(_FROM, _TO, "AD"),
            PolicyActivity,
            lambda items: items[0].policy_name
            == "Deny access to Security Vulnerabilities",
            id="top-policies",
        ),
    ],
)
def test_async_dashboard_endpoint(
    url_suffix: str,
    raw: list[dict[str, Any]],
    method_call: Callable[[AsyncDashboardService], Any],
    expected_type: type,
    extra_assert: Callable[[list[Any]], bool],
):
    client = mock(httpx.AsyncClient)
    service = AsyncDashboardService(client)
    when(client).get(f"{_BASE_PATH}{url_suffix}").thenReturn(_data_envelope(raw))

    items = asyncio.run(method_call(service))

    assert len(items) == 1
    assert isinstance(items[0], expected_type)
    assert extra_assert(items)
