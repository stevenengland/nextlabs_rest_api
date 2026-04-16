from __future__ import annotations

from nextlabs_sdk._cloudaz._report_models import (
    FilterCriteria,
    FilterField,
    ReportCriteria,
    ReportFilterGeneral,
    ReportFilters,
    ReportOrderBy,
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
