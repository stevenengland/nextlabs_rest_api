from __future__ import annotations

import pytest
from pydantic import ValidationError

from nextlabs_sdk._cloudaz._report_models import (
    ApplicationUser,
    AttributeMapping,
    AttributeMappings,
    CachedPolicy,
    CachedUser,
    DeleteReportsRequest,
    EnforcementEntry,
    EnforcementTimeBucket,
)
from nextlabs_sdk._cloudaz._report_models import (
    FilterCriteria,
    FilterField,
    PolicyActivityReport,
    PolicyActivityReportDetail,
    PolicyActivityReportRequest,
    PolicyModelAction,
    ReportCriteria,
    ReportFilterGeneral,
)
from nextlabs_sdk._cloudaz._report_models import (
    ReportFilters,
    ReportOrderBy,
    ReportWidget,
    ResourceActions,
    UserGroup,
    WidgetData,
)


def test_filter_field_construction() -> None:
    field = FilterField(
        name="log_level",
        operator="in",
        value=["3"],
        has_multi_value=False,
        function="",
    )
    assert field.name == "log_level"
    assert field.operator == "in"
    assert field.value == ["3"]
    assert field.has_multi_value is False


def test_filter_field_optional_defaults() -> None:
    field = FilterField(name="action", operator="in")
    assert field.value is None
    assert field.has_multi_value is None
    assert field.function is None


def test_filter_field_round_trip_serialization() -> None:
    raw = {
        "name": "policy_decision",
        "operator": "in",
        "value": ["A", "D"],
        "has_multi_value": False,
        "function": "",
    }
    field = FilterField.model_validate(raw)
    dumped = field.model_dump(exclude_none=True)
    assert dumped == raw


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


# --- ReportWidget ---


def test_report_widget_from_api_payload() -> None:
    raw = {
        "id": 1,
        "name": "enforcement",
        "title": "Enforcement Trend",
        "enabled": True,
        "chartType": "line",
        "attributeName": "decision",
        "maxSize": 10,
    }
    widget = ReportWidget.model_validate(raw)
    assert widget.chart_type == "line"
    assert widget.attribute_name == "decision"
    assert widget.max_size == 10


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


def test_delete_request_with_ids() -> None:
    req = DeleteReportsRequest(report_ids=[5, 10, 15])
    payload = req.model_dump(by_alias=True, exclude_none=True)
    assert payload["reportIds"] == [5, 10, 15]
    assert "title" not in payload


def test_delete_request_with_query() -> None:
    req = DeleteReportsRequest(title="Deny", policy_decision="AD")
    payload = req.model_dump(by_alias=True, exclude_none=True)
    assert payload["title"] == "Deny"
    assert payload["policyDecision"] == "AD"
    assert "reportIds" not in payload


# --- PolicyActivityReport (response) ---


def test_policy_activity_report_from_api_payload() -> None:
    raw = {
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
    report = PolicyActivityReport.model_validate(raw)
    assert report.id == 8
    assert report.title == "Allow Enforcement in Last 7 Days"
    assert report.shared_mode == "public"
    assert report.date_mode == "Relative"
    assert report.window_mode == "last_7_days"


def test_policy_activity_report_is_frozen() -> None:
    raw = {
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
    report = PolicyActivityReport.model_validate(raw)
    with pytest.raises(ValidationError):
        report.title = "changed"  # type: ignore[misc]


# --- PolicyActivityReportDetail ---


def test_report_detail_from_api_payload() -> None:
    raw = {
        "criteria": {
            "filters": {
                "general": {"type": "custom", "date_mode": "fixed"},
            },
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
    detail = PolicyActivityReportDetail.model_validate(raw)
    assert detail.criteria.filters is not None
    assert detail.criteria.filters.general is not None
    assert detail.criteria.filters.general.type == "custom"
    assert len(detail.widgets) == 1
    assert detail.widgets[0].chart_type == "line"


# --- EnforcementEntry ---


def test_enforcement_entry_from_api_payload() -> None:
    raw = {
        "POLICY_NAME": "Encryption Policy",
        "ACTION": "SELECT",
        "FROM_RESOURCE_NAME": "file1.txt",
        "TIME": "2024-10-07T07:26:14.556+00:00",
        "USER_NAME": "user@example.com",
        "ACTION_SHORT_CODE": "e3",
        "ROW_ID": 2,
        "POLICY_DECISION": "A",
    }
    entry = EnforcementEntry.model_validate(raw)
    assert entry.row_id == 2
    assert entry.policy_name == "Encryption Policy"
    assert entry.user_name == "user@example.com"
    assert entry.action == "SELECT"


def test_enforcement_entry_allows_extra_fields() -> None:
    raw = {
        "ROW_ID": 1,
        "TIME": "2024-01-01",
        "CUSTOM_COLUMN": "custom_value",
        "ANOTHER_DYNAMIC": 42,
    }
    entry = EnforcementEntry.model_validate(raw)
    assert entry.row_id == 1
    extra = entry.model_extra
    assert extra is not None
    assert extra["CUSTOM_COLUMN"] == "custom_value"
    assert extra["ANOTHER_DYNAMIC"] == 42


def test_enforcement_entry_optional_fields() -> None:
    raw = {"ROW_ID": 1, "TIME": "2024-01-01"}
    entry = EnforcementEntry.model_validate(raw)
    assert entry.row_id == 1
    assert entry.policy_name is None
    assert entry.action is None


def test_enforcement_entry_is_frozen() -> None:
    raw = {"ROW_ID": 1, "TIME": "2024-01-01"}
    entry = EnforcementEntry.model_validate(raw)
    with pytest.raises(ValidationError):
        entry.row_id = 99  # type: ignore[misc]


# --- WidgetData ---


def test_widget_data_from_api_payload() -> None:
    raw = {
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
    data = WidgetData.model_validate(raw)
    assert len(data.enforcements) == 2
    assert data.enforcements[0].hour == 1708070400000
    assert data.enforcements[0].allow_count == 5
    assert data.enforcements[0].deny_count == 2
    assert data.enforcements[0].decision_count == 7


def test_widget_data_empty_enforcements_default() -> None:
    data = WidgetData.model_validate({})
    assert data.enforcements == []


def test_enforcement_time_bucket_is_frozen() -> None:
    bucket = EnforcementTimeBucket.model_validate(
        {"hour": 100, "allowCount": 1, "denyCount": 0, "decisionCount": 1}
    )
    with pytest.raises(ValidationError):
        bucket.hour = 200  # type: ignore[misc]


# --- Cached Data ---


def test_cached_user_from_api_payload() -> None:
    raw = {
        "displayName": "LocalSystem@localhost",
        "firstName": "User",
        "lastName": "System",
    }
    user = CachedUser.model_validate(raw)
    assert user.display_name == "LocalSystem@localhost"
    assert user.first_name == "User"


def test_cached_policy_from_api_payload() -> None:
    raw = {"name": "Test", "fullName": "/ROOT_187/Testing Policy"}
    policy = CachedPolicy.model_validate(raw)
    assert policy.name == "Test"
    assert policy.full_name == "/ROOT_187/Testing Policy"


def test_policy_model_action_from_api_payload() -> None:
    raw = {"policyModelId": 43, "label": "action1", "shortCode": "dw"}
    action = PolicyModelAction.model_validate(raw)
    assert action.policy_model_id == 43
    assert action.label == "action1"
    assert action.short_code == "dw"


def test_resource_actions_from_api_payload() -> None:
    raw = {
        "policyModelActions": {
            "testing resource type": [
                {"policyModelId": 43, "label": "action1", "shortCode": "dw"},
            ],
        },
    }
    result = ResourceActions.model_validate(raw)
    assert "testing resource type" in result.policy_model_actions
    assert result.policy_model_actions["testing resource type"][0].label == "action1"


def test_attribute_mapping_from_api_payload() -> None:
    raw = {
        "id": 11,
        "name": "FROM_RESOURCE_NAME",
        "mappedColumn": "FROM_RESOURCE_NAME",
        "dataType": "STRING",
        "attrType": "RESOURCE",
        "isDynamic": False,
    }
    mapping = AttributeMapping.model_validate(raw)
    assert mapping.mapped_column == "FROM_RESOURCE_NAME"
    assert mapping.data_type == "STRING"
    assert mapping.is_dynamic is False


def test_attribute_mappings_from_api_payload() -> None:
    raw = {
        "resource": [
            {
                "id": 11,
                "name": "FROM_RESOURCE_NAME",
                "mappedColumn": "FROM_RESOURCE_NAME",
                "dataType": "STRING",
                "attrType": "RESOURCE",
                "isDynamic": False,
            },
        ],
        "user": [
            {
                "id": 2,
                "name": "USER_NAME",
                "mappedColumn": "USER_NAME",
                "dataType": "STRING",
                "attrType": "USER",
                "isDynamic": False,
            },
        ],
        "others": [
            {
                "id": 1,
                "name": "DATE",
                "mappedColumn": "TIME",
                "dataType": "TIMESTAMP",
                "attrType": "OTHERS",
                "isDynamic": False,
            },
        ],
    }
    mappings = AttributeMappings.model_validate(raw)
    assert len(mappings.resource) == 1
    assert len(mappings.user) == 1
    assert len(mappings.others) == 1


# --- Sharing ---


def test_user_group_from_api_payload() -> None:
    raw = {"title": "All Policy Server Users", "id": 1}
    group = UserGroup.model_validate(raw)
    assert group.id == 1
    assert group.title == "All Policy Server Users"


def test_application_user_from_api_payload() -> None:
    raw = {"firstName": "Test", "lastName": "User", "username": "testuser"}
    user = ApplicationUser.model_validate(raw)
    assert user.first_name == "Test"
    assert user.username == "testuser"
