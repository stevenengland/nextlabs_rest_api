from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from nextlabs_sdk._cloudaz._report_models import (
    ApplicationUser,
    AttributeMapping,
    AttributeMappings,
    CachedPolicy,
    CachedUser,
    DeleteReportsRequest,
    EnforcementEntry,
    EnforcementTimeBucket,
    FilterCriteria,
    FilterField,
    PolicyActivityReport,
    PolicyActivityReportDetail,
    PolicyActivityReportRequest,
    PolicyModelAction,
    ReportCriteria,
    ReportFilterGeneral,
    ReportFilters,
    ReportOrderBy,
    ReportWidget,
    SaveInfo,
    ResourceActions,
    UserGroup,
    WidgetData,
)

# --- FilterField ---


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        pytest.param(
            dict(
                name="log_level",
                operator="in",
                value=["3"],
                has_multi_value=False,
                function="",
            ),
            {
                "name": "log_level",
                "operator": "in",
                "value": ["3"],
                "has_multi_value": False,
            },
            id="full",
        ),
        pytest.param(
            dict(name="action", operator="in"),
            {"value": None, "has_multi_value": None, "function": None},
            id="defaults",
        ),
    ],
)
def test_filter_field_construction(
    kwargs: dict[str, Any], expected: dict[str, Any]
) -> None:
    field = FilterField(**kwargs)
    for attr, val in expected.items():
        assert getattr(field, attr) == val


def test_filter_field_round_trip_serialization() -> None:
    raw = {
        "name": "policy_decision",
        "operator": "in",
        "value": ["A", "D"],
        "has_multi_value": False,
        "function": "",
    }
    assert FilterField.model_validate(raw).model_dump(exclude_none=True) == raw


# --- FilterCriteria ---


def test_filter_criteria_with_look_up_field() -> None:
    criteria = FilterCriteria(
        look_up_field=FilterField(
            name="user_name",
            operator="in",
            value=[],
            has_multi_value=True,
            function="",
        ),
        fields=[],
    )
    assert criteria.look_up_field is not None
    assert criteria.look_up_field.name == "user_name"


def test_filter_criteria_optional_defaults() -> None:
    criteria = FilterCriteria()
    assert criteria.look_up_field is None
    assert criteria.fields is None


# --- Report structures ---


def test_report_filter_general_construction() -> None:
    general = ReportFilterGeneral(
        type="custom",
        date_mode="fixed",
        window_mode="",
        start_date="2024-02-01 00:00:00.0",
        end_date="2024-02-29 23:59:59.0",
        fields=[FilterField(name="log_level", operator="in", value=["3"])],
    )
    assert general.type == "custom"
    assert general.date_mode == "fixed"
    assert general.start_date == "2024-02-01 00:00:00.0"
    assert general.fields is not None
    assert len(general.fields) == 1


def test_report_filters_full_construction() -> None:
    filters = ReportFilters(
        general=ReportFilterGeneral(type="custom"),
        user_criteria=FilterCriteria(),
        resource_criteria=FilterCriteria(),
        policy_criteria=FilterCriteria(),
        other_criteria=FilterCriteria(),
    )
    assert filters.general is not None
    assert filters.general.type == "custom"


def test_report_order_by_construction() -> None:
    order = ReportOrderBy(col_name="time", sort_order="descending")
    assert order.col_name == "time"
    assert order.sort_order == "descending"


def test_report_criteria_full_construction() -> None:
    criteria = ReportCriteria(
        filters=ReportFilters(general=ReportFilterGeneral(type="custom")),
        header=["USER_NAME", "FROM_RESOURCE_NAME", "POLICY_NAME"],
        order_by=[ReportOrderBy(col_name="time", sort_order="descending")],
        pagesize=20,
        max_rows=10000,
        grouping_mode="none",
        group_by=[],
    )
    assert criteria.pagesize == 20
    assert criteria.max_rows == 10000
    assert criteria.header is not None
    assert len(criteria.header) == 3
    assert criteria.order_by is not None
    assert criteria.order_by[0].col_name == "time"


def test_report_criteria_optional_defaults() -> None:
    criteria = ReportCriteria()
    assert criteria.filters is None
    assert criteria.header is None
    assert criteria.order_by is None
    assert criteria.pagesize is None


def test_report_criteria_round_trip_from_api_response() -> None:
    raw = {
        "filters": {
            "general": {
                "type": "custom",
                "date_mode": "fixed",
                "window_mode": "",
                "start_date": "2024-02-01 00:00:00.0",
                "end_date": "2024-02-29 23:59:59.0",
                "fields": [
                    {
                        "name": "log_level",
                        "operator": "in",
                        "value": ["3"],
                        "has_multi_value": False,
                        "function": "",
                    },
                ],
            },
            "user_criteria": {
                "look_up_field": {
                    "name": "user_name",
                    "operator": "in",
                    "value": [],
                    "has_multi_value": True,
                    "function": "",
                },
                "fields": [],
            },
        },
        "header": ["USER_NAME", "POLICY_NAME"],
        "order_by": [{"col_name": "time", "sort_order": "descending"}],
        "pagesize": 20,
        "max_rows": 10000,
        "grouping_mode": "none",
        "group_by": [],
    }
    criteria = ReportCriteria.model_validate(raw)
    assert criteria.filters is not None
    assert criteria.filters.general is not None
    assert criteria.filters.general.type == "custom"
    assert criteria.filters.user_criteria is not None
    assert criteria.filters.user_criteria.look_up_field is not None
    assert criteria.filters.user_criteria.look_up_field.name == "user_name"
    assert criteria.pagesize == 20


# --- SaveInfo ---


def test_save_info_round_trip() -> None:
    raw = {
        "report_name": "Q1 Enforcement",
        "report_desc": "Quarterly review",
        "report_type": "custom",
        "shared_mode": "private",
        "user_ids": ["alice", "bob"],
        "group_ids": [1, 2, 3],
    }
    info = SaveInfo.model_validate(raw)
    assert info.report_name == "Q1 Enforcement"
    assert info.user_ids == ["alice", "bob"]
    assert info.group_ids == [1, 2, 3]
    assert info.model_dump(exclude_none=True) == raw


def test_save_info_defaults_all_optional() -> None:
    info = SaveInfo()
    assert info.report_name is None
    assert info.user_ids is None
    assert info.group_ids is None


# --- ReportCriteria: aggregators / save_info / extra ---


def test_report_criteria_preserves_aggregators_and_save_info() -> None:
    raw = {
        "pagesize": 20,
        "aggregators": [
            {"name": "decision", "operator": "count"},
            {"name": "user_name", "operator": "group"},
        ],
        "save_info": {
            "report_name": "Audit",
            "shared_mode": "shared",
            "group_ids": [7],
        },
    }
    criteria = ReportCriteria.model_validate(raw)
    assert criteria.aggregators is not None
    assert len(criteria.aggregators) == 2
    assert criteria.aggregators[0].name == "decision"
    assert criteria.save_info is not None
    assert criteria.save_info.report_name == "Audit"
    assert criteria.save_info.group_ids == [7]


def test_report_criteria_allows_unknown_fields() -> None:
    criteria = ReportCriteria.model_validate({"pagesize": 10, "future_field": "x"})
    dumped = criteria.model_dump()
    assert dumped.get("future_field") == "x"


# --- ReportWidget ---


def test_report_widget_from_api_payload() -> None:
    widget = ReportWidget.model_validate(
        {
            "id": 1,
            "key": "enforcements",
            "name": "enforcement",
            "title": "Enforcement Trend",
            "enabled": True,
            "chartType": "line",
            "attributeName": "decision",
            "maxSize": 10,
        }
    )
    assert widget.key == "enforcements"
    assert widget.chart_type == "line"
    assert widget.attribute_name == "decision"
    assert widget.max_size == 10


def test_report_widget_allows_unknown_fields() -> None:
    widget = ReportWidget.model_validate(
        {
            "name": "enforcement",
            "title": "Trend",
            "chartType": "line",
            "attributeName": "decision",
            "new_server_field": 42,
        }
    )
    dumped = widget.model_dump()
    assert dumped.get("new_server_field") == 42


def test_report_widget_python_construction() -> None:
    widget = ReportWidget(
        name="enforcement",
        title="Enforcement Trend",
        chart_type="line",
        attribute_name="decision",
    )
    assert widget.chart_type == "line"
    dumped = widget.model_dump(by_alias=True, exclude_none=True)
    assert dumped["chartType"] == "line"
    assert dumped["attributeName"] == "decision"
    assert "maxSize" not in dumped


# --- PolicyActivityReportRequest ---


def test_report_request_serialization() -> None:
    request = PolicyActivityReportRequest(
        criteria=ReportCriteria(
            filters=ReportFilters(
                general=ReportFilterGeneral(type="custom", date_mode="fixed"),
            ),
        ),
        widgets=[
            ReportWidget(
                name="enforcement",
                title="Trend",
                chart_type="line",
                attribute_name="decision",
            ),
        ],
    )
    payload = request.model_dump(by_alias=True, exclude_none=True)
    assert payload["criteria"]["filters"]["general"]["type"] == "custom"
    assert payload["widgets"][0]["chartType"] == "line"


# --- DeleteReportsRequest ---


@pytest.mark.parametrize(
    "kwargs,present,absent",
    [
        pytest.param(
            {"report_ids": [5, 10, 15]},
            {"reportIds": [5, 10, 15]},
            ("title",),
            id="with-ids",
        ),
        pytest.param(
            {"title": "Deny", "policy_decision": "AD"},
            {"title": "Deny", "policyDecision": "AD"},
            ("reportIds",),
            id="with-query",
        ),
        pytest.param(
            {"title": "Deny", "shared": True},
            {"title": "Deny", "shared": True},
            ("reportIds", "policyDecision"),
            id="with-shared",
        ),
        pytest.param(
            {"report_ids": [1], "shared": False},
            {"reportIds": [1], "shared": False},
            ("title", "policyDecision"),
            id="with-shared-false",
        ),
    ],
)
def test_delete_request(
    kwargs: dict[str, Any],
    present: dict[str, Any],
    absent: tuple[str, ...],
) -> None:
    payload = DeleteReportsRequest(**kwargs).model_dump(
        by_alias=True, exclude_none=True
    )
    for key, value in present.items():
        assert payload[key] == value
    for key in absent:
        assert key not in payload


# --- PolicyActivityReport ---


def test_policy_activity_report_from_api_payload() -> None:
    report = PolicyActivityReport.model_validate(
        {
            "id": 8,
            "title": "Allow Enforcement in Last 7 Days",
            "description": "Allow Enforcement in Last 7 Days v1.0",
            "sharedMode": "public",
            "decision": "A",
            "dateMode": "Relative",
            "windowMode": "last_7_days",
            "startDate": "2024-08-14T03:05:16.148+00:00",
            "endDate": "2024-08-21T03:05:16.148+00:00",
            "lastUpdatedDate": "2024-08-18T02:17:23.484+00:00",
            "type": "report",
        }
    )
    assert report.id == 8
    assert report.title == "Allow Enforcement in Last 7 Days"
    assert report.shared_mode == "public"
    assert report.date_mode == "Relative"
    assert report.window_mode == "last_7_days"


def test_policy_activity_report_is_frozen() -> None:
    report = PolicyActivityReport.model_validate(
        {
            "id": 1,
            "title": "T",
            "sharedMode": "public",
            "decision": "A",
            "dateMode": "fixed",
            "windowMode": "",
            "startDate": "2024-01-01",
            "endDate": "2024-01-31",
            "lastUpdatedDate": "2024-01-15",
            "type": "custom",
        }
    )
    with pytest.raises(ValidationError):
        report.title = "changed"  # type: ignore[misc]


# --- PolicyActivityReportDetail ---


def test_report_detail_from_api_payload() -> None:
    detail = PolicyActivityReportDetail.model_validate(
        {
            "criteria": {
                "filters": {"general": {"type": "custom", "date_mode": "fixed"}},
                "header": ["USER_NAME"],
                "pagesize": 20,
            },
            "widgets": [
                {
                    "id": 1,
                    "name": "enforcement",
                    "title": "Trend",
                    "enabled": True,
                    "chartType": "line",
                    "attributeName": "decision",
                    "maxSize": 10,
                },
            ],
        }
    )
    assert detail.criteria.filters is not None
    assert detail.criteria.filters.general is not None
    assert detail.criteria.filters.general.type == "custom"
    assert len(detail.widgets) == 1
    assert detail.widgets[0].chart_type == "line"


# --- EnforcementEntry ---


def test_enforcement_entry_from_api_payload() -> None:
    entry = EnforcementEntry.model_validate(
        {
            "POLICY_NAME": "Encryption Policy",
            "ACTION": "SELECT",
            "FROM_RESOURCE_NAME": "file1.txt",
            "TIME": "2024-10-07T07:26:14.556+00:00",
            "USER_NAME": "user@example.com",
            "ACTION_SHORT_CODE": "e3",
            "ROW_ID": 2,
            "POLICY_DECISION": "A",
        }
    )
    assert entry.row_id == 2
    assert entry.policy_name == "Encryption Policy"
    assert entry.user_name == "user@example.com"
    assert entry.action == "SELECT"


def test_enforcement_entry_allows_extra_fields() -> None:
    entry = EnforcementEntry.model_validate(
        {
            "ROW_ID": 1,
            "TIME": "2024-01-01",
            "CUSTOM_COLUMN": "custom_value",
            "ANOTHER_DYNAMIC": 42,
        }
    )
    assert entry.row_id == 1
    extra = entry.model_extra
    assert extra is not None
    assert extra["CUSTOM_COLUMN"] == "custom_value"
    assert extra["ANOTHER_DYNAMIC"] == 42


def test_enforcement_entry_optional_fields() -> None:
    entry = EnforcementEntry.model_validate({"ROW_ID": 1, "TIME": "2024-01-01"})
    assert entry.row_id == 1
    assert entry.policy_name is None
    assert entry.action is None


def test_enforcement_entry_is_frozen() -> None:
    entry = EnforcementEntry.model_validate({"ROW_ID": 1, "TIME": "2024-01-01"})
    with pytest.raises(ValidationError):
        entry.row_id = 99  # type: ignore[misc]


# --- WidgetData ---


def test_widget_data_from_api_payload() -> None:
    data = WidgetData.model_validate(
        {
            "enforcements": [
                {
                    "hour": 1708070400000,
                    "allowCount": 5,
                    "denyCount": 2,
                    "decisionCount": 7,
                },
                {
                    "hour": 1708117200000,
                    "allowCount": 0,
                    "denyCount": 0,
                    "decisionCount": 0,
                },
            ],
        }
    )
    assert len(data.enforcements) == 2
    assert data.enforcements[0].hour == 1708070400000
    assert data.enforcements[0].allow_count == 5
    assert data.enforcements[0].deny_count == 2
    assert data.enforcements[0].decision_count == 7


def test_widget_data_empty_enforcements_default() -> None:
    assert WidgetData.model_validate({}).enforcements == []


def test_enforcement_time_bucket_is_frozen() -> None:
    bucket = EnforcementTimeBucket.model_validate(
        {"hour": 100, "allowCount": 1, "denyCount": 0, "decisionCount": 1},
    )
    with pytest.raises(ValidationError):
        bucket.hour = 200  # type: ignore[misc]


# --- Simple model-validate pairs ---


def _attr_mapping_raw() -> dict[str, Any]:
    return {
        "id": 11,
        "name": "FROM_RESOURCE_NAME",
        "mappedColumn": "FROM_RESOURCE_NAME",
        "dataType": "STRING",
        "attrType": "RESOURCE",
        "isDynamic": False,
    }


def _user_mapping_raw() -> dict[str, Any]:
    return {
        "id": 2,
        "name": "USER_NAME",
        "mappedColumn": "USER_NAME",
        "dataType": "STRING",
        "attrType": "USER",
        "isDynamic": False,
    }


def _others_mapping_raw() -> dict[str, Any]:
    return {
        "id": 1,
        "name": "DATE",
        "mappedColumn": "TIME",
        "dataType": "TIMESTAMP",
        "attrType": "OTHERS",
        "isDynamic": False,
    }


@pytest.mark.parametrize(
    "model,raw,expected",
    [
        pytest.param(
            CachedUser,
            {
                "displayName": "LocalSystem@localhost",
                "firstName": "User",
                "lastName": "System",
            },
            {"display_name": "LocalSystem@localhost", "first_name": "User"},
            id="cached-user",
        ),
        pytest.param(
            CachedPolicy,
            {"name": "Test", "fullName": "/ROOT_187/Testing Policy"},
            {"name": "Test", "full_name": "/ROOT_187/Testing Policy"},
            id="cached-policy",
        ),
        pytest.param(
            PolicyModelAction,
            {"policyModelId": 43, "label": "action1", "shortCode": "dw"},
            {"policy_model_id": 43, "label": "action1", "short_code": "dw"},
            id="policy-model-action",
        ),
        pytest.param(
            AttributeMapping,
            _attr_mapping_raw(),
            {
                "mapped_column": "FROM_RESOURCE_NAME",
                "data_type": "STRING",
                "is_dynamic": False,
            },
            id="attribute-mapping",
        ),
        pytest.param(
            UserGroup,
            {"title": "All Policy Server Users", "id": 1},
            {"id": 1, "title": "All Policy Server Users"},
            id="user-group",
        ),
        pytest.param(
            ApplicationUser,
            {"firstName": "Test", "lastName": "User", "username": "testuser"},
            {"first_name": "Test", "username": "testuser"},
            id="application-user",
        ),
    ],
)
def test_simple_model_validate(
    model: type[BaseModel],
    raw: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    obj = model.model_validate(raw)
    for attr, value in expected.items():
        assert getattr(obj, attr) == value


def test_resource_actions_from_api_payload() -> None:
    result = ResourceActions.model_validate(
        {
            "policyModelActions": {
                "testing resource type": [
                    {"policyModelId": 43, "label": "action1", "shortCode": "dw"},
                ],
            },
        }
    )
    assert "testing resource type" in result.policy_model_actions
    assert result.policy_model_actions["testing resource type"][0].label == "action1"


def test_attribute_mappings_from_api_payload() -> None:
    mappings = AttributeMappings.model_validate(
        {
            "resource": [_attr_mapping_raw()],
            "user": [_user_mapping_raw()],
            "others": [_others_mapping_raw()],
        }
    )
    assert len(mappings.resource) == 1
    assert len(mappings.user) == 1
    assert len(mappings.others) == 1
