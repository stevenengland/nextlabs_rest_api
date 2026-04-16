from __future__ import annotations

import asyncio

import httpx
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


def test_async_latest_alerts() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncDashboardService(client)

    raw_alerts = [
        {
            "level": "L3",
            "alertMessage": "",
            "monitorName": "Deny Policy",
            "triggeredAt": "2024-02-22T15:55:27.407+00:00",
        },
    ]
    response = _make_data_envelope(raw_alerts)
    when(client).get(
        f"{_BASE_PATH}/latestAlerts/1708560000000/1708646400000"
    ).thenReturn(response)

    async def run() -> list[Alert]:
        return await service.latest_alerts(1708560000000, 1708646400000)

    alerts = asyncio.run(run())
    assert len(alerts) == 1
    assert isinstance(alerts[0], Alert)
    assert alerts[0].monitor_name == "Deny Policy"


def test_async_alerts_by_monitor_tags() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncDashboardService(client)

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

    async def run() -> list[MonitorTagAlert]:
        return await service.alerts_by_monitor_tags(1708560000000, 1708646400000)

    tag_alerts = asyncio.run(run())
    assert len(tag_alerts) == 1
    assert isinstance(tag_alerts[0], MonitorTagAlert)


def test_async_top_users() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncDashboardService(client)

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

    async def run() -> list[ActivityByEntity]:
        return await service.top_users(1708560000000, 1708646400000, "AD")

    users = asyncio.run(run())
    assert len(users) == 1
    assert isinstance(users[0], ActivityByEntity)
    assert users[0].name == "John Mason"


def test_async_top_resources() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncDashboardService(client)

    raw = [
        {
            "name": "sap://resource/1",
            "allowCount": 480,
            "denyCount": 488,
            "decisionCount": 968,
        },
    ]
    response = _make_data_envelope(raw)
    when(client).get(
        f"{_BASE_PATH}/activityByResources/1708560000000/1708646400000/AD"
    ).thenReturn(response)

    async def run() -> list[ActivityByEntity]:
        return await service.top_resources(1708560000000, 1708646400000, "AD")

    resources = asyncio.run(run())
    assert len(resources) == 1
    assert isinstance(resources[0], ActivityByEntity)
    assert resources[0].decision_count == 968


def test_async_top_policies() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncDashboardService(client)

    raw = [
        {
            "policy_decisions": [
                {"day_nb": 1680505200000, "allow_count": 17, "deny_count": 13},
            ],
            "policy_name": "Deny access to Security Vulnerabilities",
        },
    ]
    response = _make_data_envelope(raw)
    when(client).get(
        f"{_BASE_PATH}/activityByPolicies/1708560000000/1708646400000/AD"
    ).thenReturn(response)

    async def run() -> list[PolicyActivity]:
        return await service.top_policies(1708560000000, 1708646400000, "AD")

    policies = asyncio.run(run())
    assert len(policies) == 1
    assert isinstance(policies[0], PolicyActivity)
    assert policies[0].policy_name == "Deny access to Security Vulnerabilities"
