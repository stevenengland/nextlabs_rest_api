from __future__ import annotations

import httpx

from nextlabs_sdk._cloudaz._dashboard_models import (
    ActivityByEntity,
    Alert,
    MonitorTagAlert,
    PolicyActivity,
)
from nextlabs_sdk._cloudaz._response import parse_data

_BASE_PATH = "/nextlabs-reporter/api/v1/dashboard"


class DashboardService:
    """Synchronous service for reporter dashboard endpoints."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def latest_alerts(self, from_date: int, to_date: int) -> list[Alert]:
        """Retrieve the latest alerts between from_date and to_date (epoch ms)."""
        response = self._client.get(f"{_BASE_PATH}/latestAlerts/{from_date}/{to_date}")
        raw = parse_data(response)
        return [Alert.model_validate(entry) for entry in raw]

    def alerts_by_monitor_tags(
        self, from_date: int, to_date: int
    ) -> list[MonitorTagAlert]:
        """Retrieve alert counts grouped by monitor tags."""
        response = self._client.get(
            f"{_BASE_PATH}/alertByMonitorTags/{from_date}/{to_date}"
        )
        raw = parse_data(response)
        return [MonitorTagAlert.model_validate(entry) for entry in raw]

    def top_users(
        self, from_date: int, to_date: int, policy_decision: str
    ) -> list[ActivityByEntity]:
        """Retrieve top users by enforcement activity."""
        response = self._client.get(
            f"{_BASE_PATH}/activityByUsers/{from_date}/{to_date}/{policy_decision}"
        )
        raw = parse_data(response)
        return [ActivityByEntity.model_validate(entry) for entry in raw]

    def top_resources(
        self, from_date: int, to_date: int, policy_decision: str
    ) -> list[ActivityByEntity]:
        """Retrieve top resources by enforcement activity."""
        response = self._client.get(
            f"{_BASE_PATH}/activityByResources/{from_date}/{to_date}/{policy_decision}"
        )
        raw = parse_data(response)
        return [ActivityByEntity.model_validate(entry) for entry in raw]

    def top_policies(
        self, from_date: int, to_date: int, policy_decision: str
    ) -> list[PolicyActivity]:
        """Retrieve top policies with daily trend data."""
        response = self._client.get(
            f"{_BASE_PATH}/activityByPolicies/{from_date}/{to_date}/{policy_decision}"
        )
        raw = parse_data(response)
        return [PolicyActivity.model_validate(entry) for entry in raw]


class AsyncDashboardService:
    """Asynchronous service for reporter dashboard endpoints."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def latest_alerts(self, from_date: int, to_date: int) -> list[Alert]:
        """Retrieve the latest alerts between from_date and to_date (epoch ms)."""
        response = await self._client.get(
            f"{_BASE_PATH}/latestAlerts/{from_date}/{to_date}"
        )
        raw = parse_data(response)
        return [Alert.model_validate(entry) for entry in raw]

    async def alerts_by_monitor_tags(
        self, from_date: int, to_date: int
    ) -> list[MonitorTagAlert]:
        """Retrieve alert counts grouped by monitor tags."""
        response = await self._client.get(
            f"{_BASE_PATH}/alertByMonitorTags/{from_date}/{to_date}"
        )
        raw = parse_data(response)
        return [MonitorTagAlert.model_validate(entry) for entry in raw]

    async def top_users(
        self, from_date: int, to_date: int, policy_decision: str
    ) -> list[ActivityByEntity]:
        """Retrieve top users by enforcement activity."""
        response = await self._client.get(
            f"{_BASE_PATH}/activityByUsers/{from_date}/{to_date}/{policy_decision}"
        )
        raw = parse_data(response)
        return [ActivityByEntity.model_validate(entry) for entry in raw]

    async def top_resources(
        self, from_date: int, to_date: int, policy_decision: str
    ) -> list[ActivityByEntity]:
        """Retrieve top resources by enforcement activity."""
        response = await self._client.get(
            f"{_BASE_PATH}/activityByResources/{from_date}/{to_date}/{policy_decision}"
        )
        raw = parse_data(response)
        return [ActivityByEntity.model_validate(entry) for entry in raw]

    async def top_policies(
        self, from_date: int, to_date: int, policy_decision: str
    ) -> list[PolicyActivity]:
        """Retrieve top policies with daily trend data."""
        response = await self._client.get(
            f"{_BASE_PATH}/activityByPolicies/{from_date}/{to_date}/{policy_decision}"
        )
        raw = parse_data(response)
        return [PolicyActivity.model_validate(entry) for entry in raw]
