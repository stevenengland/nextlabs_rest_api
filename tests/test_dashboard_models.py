from __future__ import annotations

import pytest

from nextlabs_sdk._cloudaz._dashboard_models import (
    ActivityByEntity,
    Alert,
    MonitorTagAlert,
    PolicyActivity,
    PolicyDayBucket,
)


def test_alert_from_api_response() -> None:
    raw = {
        "level": "L3",
        "alertMessage": "",
        "monitorName": "Deny Policy",
        "triggeredAt": "2024-02-22T15:55:27.407+00:00",
    }
    alert = Alert.model_validate(raw)
    assert alert.level == "L3"
    assert alert.alert_message == ""
    assert alert.monitor_name == "Deny Policy"
    assert alert.triggered_at == "2024-02-22T15:55:27.407+00:00"


def test_alert_is_frozen() -> None:
    alert = Alert.model_validate(
        {
            "level": "L3",
            "alertMessage": "",
            "monitorName": "Test",
            "triggeredAt": "2024-01-01T00:00:00.000+00:00",
        }
    )
    with pytest.raises(Exception):
        alert.level = "L1"  # type: ignore[misc]


def test_monitor_tag_alert_from_api_response() -> None:
    raw = {
        "tagValue": "Weekly Monitoring",
        "monitorName": "Deny Policy",
        "alertCount": 1,
    }
    tag_alert = MonitorTagAlert.model_validate(raw)
    assert tag_alert.tag_value == "Weekly Monitoring"
    assert tag_alert.monitor_name == "Deny Policy"
    assert tag_alert.alert_count == 1


def test_activity_by_entity_from_api_response() -> None:
    raw = {
        "name": "John Mason",
        "allowCount": 360,
        "denyCount": 428,
        "decisionCount": 788,
    }
    entity = ActivityByEntity.model_validate(raw)
    assert entity.name == "John Mason"
    assert entity.allow_count == 360
    assert entity.deny_count == 428
    assert entity.decision_count == 788


def test_activity_by_entity_is_frozen() -> None:
    entity = ActivityByEntity.model_validate(
        {
            "name": "Test",
            "allowCount": 0,
            "denyCount": 0,
            "decisionCount": 0,
        }
    )
    with pytest.raises(Exception):
        entity.name = "Changed"  # type: ignore[misc]


def test_policy_day_bucket_from_api_response() -> None:
    raw = {
        "day_nb": 1680505200000,
        "allow_count": 17,
        "deny_count": 13,
    }
    bucket = PolicyDayBucket.model_validate(raw)
    assert bucket.day_nb == 1680505200000
    assert bucket.allow_count == 17
    assert bucket.deny_count == 13


def test_policy_activity_from_api_response() -> None:
    raw = {
        "policy_decisions": [
            {"day_nb": 1680505200000, "allow_count": 17, "deny_count": 13},
            {"day_nb": 1680591600000, "allow_count": 13, "deny_count": 10},
        ],
        "policy_name": "Deny access to Security Vulnerabilities",
    }
    activity = PolicyActivity.model_validate(raw)
    assert activity.policy_name == "Deny access to Security Vulnerabilities"
    assert len(activity.policy_decisions) == 2
    assert activity.policy_decisions[0].day_nb == 1680505200000
    assert activity.policy_decisions[0].allow_count == 17


def test_policy_activity_is_frozen() -> None:
    activity = PolicyActivity.model_validate(
        {
            "policy_decisions": [],
            "policy_name": "Test",
        }
    )
    with pytest.raises(Exception):
        activity.policy_name = "Changed"  # type: ignore[misc]
