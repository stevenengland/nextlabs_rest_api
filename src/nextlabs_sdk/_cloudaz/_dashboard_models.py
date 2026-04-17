from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Alert(BaseModel):
    """A single alert from the reporter dashboard."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    level: str
    alert_message: str = Field(alias="alertMessage")
    monitor_name: str = Field(alias="monitorName")
    triggered_at: str = Field(alias="triggeredAt")


class MonitorTagAlert(BaseModel):
    """Alert count grouped by monitor tag."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    tag_value: str = Field(alias="tagValue")
    monitor_name: str = Field(alias="monitorName")
    alert_count: int = Field(alias="alertCount")


class ActivityByEntity(BaseModel):
    """Activity counts for a single entity (user or resource)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    name: str
    allow_count: int = Field(alias="allowCount")
    deny_count: int = Field(alias="denyCount")
    decision_count: int = Field(alias="decisionCount")


class PolicyDayBucket(BaseModel):
    """A single day's decision counts for a policy."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    day_nb: int
    allow_count: int
    deny_count: int


class PolicyActivity(BaseModel):
    """Activity data for a single policy, including daily trend."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    policy_name: str
    policy_decisions: list[PolicyDayBucket]

    @property
    def day_count(self) -> int:
        return len(self.policy_decisions)

    @property
    def allow_total(self) -> int:
        return sum(bucket.allow_count for bucket in self.policy_decisions)

    @property
    def deny_total(self) -> int:
        return sum(bucket.deny_count for bucket in self.policy_decisions)

    @property
    def decision_total(self) -> int:
        return self.allow_total + self.deny_total
