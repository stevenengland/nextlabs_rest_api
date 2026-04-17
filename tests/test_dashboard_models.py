from __future__ import annotations

import pytest

from nextlabs_sdk._cloudaz._dashboard_models import (
    ActivityByEntity,
    Alert,
    MonitorTagAlert,
    PolicyActivity,
    PolicyDayBucket,
)


def test_alert_from_api_response():
    alert = Alert.model_validate(
        {
            "level": "L3",
            "alertMessage": "",
            "monitorName": "Deny Policy",
            "triggeredAt": "2024-02-22T15:55:27.407+00:00",
        }
    )
    assert alert.level == "L3"
    assert alert.alert_message == ""
    assert alert.monitor_name == "Deny Policy"
    assert alert.triggered_at == "2024-02-22T15:55:27.407+00:00"


def test_monitor_tag_alert_from_api_response():
    tag_alert = MonitorTagAlert.model_validate(
        {
            "tagValue": "Weekly Monitoring",
            "monitorName": "Deny Policy",
            "alertCount": 1,
        }
    )
    assert tag_alert.tag_value == "Weekly Monitoring"
    assert tag_alert.monitor_name == "Deny Policy"
    assert tag_alert.alert_count == 1


def test_activity_by_entity_from_api_response():
    entity = ActivityByEntity.model_validate(
        {
            "name": "John Mason",
            "allowCount": 360,
            "denyCount": 428,
            "decisionCount": 788,
        }
    )
    assert entity.name == "John Mason"
    assert entity.allow_count == 360
    assert entity.deny_count == 428
    assert entity.decision_count == 788


def test_policy_day_bucket_from_api_response():
    bucket = PolicyDayBucket.model_validate(
        {"day_nb": 1680505200000, "allow_count": 17, "deny_count": 13},
    )
    assert bucket.day_nb == 1680505200000
    assert bucket.allow_count == 17
    assert bucket.deny_count == 13


def test_policy_activity_from_api_response():
    activity = PolicyActivity.model_validate(
        {
            "policy_decisions": [
                {"day_nb": 1680505200000, "allow_count": 17, "deny_count": 13},
                {"day_nb": 1680591600000, "allow_count": 13, "deny_count": 10},
            ],
            "policy_name": "Deny access to Security Vulnerabilities",
        }
    )
    assert activity.policy_name == "Deny access to Security Vulnerabilities"
    assert len(activity.policy_decisions) == 2
    assert activity.policy_decisions[0].day_nb == 1680505200000
    assert activity.policy_decisions[0].allow_count == 17


@pytest.mark.parametrize(
    "model_cls,raw,mutate",
    [
        pytest.param(
            Alert,
            {
                "level": "L3",
                "alertMessage": "",
                "monitorName": "Test",
                "triggeredAt": "2024-01-01T00:00:00.000+00:00",
            },
            ("level", "L1"),
            id="alert",
        ),
        pytest.param(
            ActivityByEntity,
            {"name": "Test", "allowCount": 0, "denyCount": 0, "decisionCount": 0},
            ("name", "Changed"),
            id="activity-by-entity",
        ),
        pytest.param(
            PolicyActivity,
            {"policy_decisions": [], "policy_name": "Test"},
            ("policy_name", "Changed"),
            id="policy-activity",
        ),
    ],
)
def test_dashboard_models_are_frozen(model_cls, raw, mutate):
    instance = model_cls.model_validate(raw)
    attr, value = mutate
    with pytest.raises(Exception):
        setattr(instance, attr, value)
