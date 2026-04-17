from __future__ import annotations

import pytest

from nextlabs_sdk._cloudaz._activity_log_query_models import (
    ActivityLogAttribute,
    ActivityLogQuery,
)


def _required() -> dict[str, object]:
    return {
        "from_date": 1716825600000,
        "to_date": 1717516799999,
        "policy_decision": "AD",
        "sort_by": "time",
        "sort_order": "ascending",
    }


def test_activity_log_query_required_fields():
    query = ActivityLogQuery(**_required())  # type: ignore[arg-type]
    assert query.from_date == 1716825600000
    assert query.to_date == 1717516799999
    assert query.policy_decision == "AD"
    assert query.sort_by == "time"
    assert query.sort_order == "ascending"
    assert query.field_name is None
    assert query.field_value is None
    assert query.header is None
    assert query.page is None
    assert query.size is None


def test_activity_log_query_serialization_aliases():
    query = ActivityLogQuery(
        **_required(),  # type: ignore[arg-type]
        field_name="host_name",
        field_value="cloudaz.nextlabs.solutions",
        header=["ROW_ID", "TIME", "USER_NAME"],
        page=0,
        size=10,
    )
    dumped = query.model_dump(by_alias=True, exclude_none=True)
    assert dumped["fromDate"] == 1716825600000
    assert dumped["toDate"] == 1717516799999
    assert dumped["policyDecision"] == "AD"
    assert dumped["sortBy"] == "time"
    assert dumped["sortOrder"] == "ascending"
    assert dumped["fieldName"] == "host_name"
    assert dumped["fieldValue"] == "cloudaz.nextlabs.solutions"
    assert dumped["header"] == ["ROW_ID", "TIME", "USER_NAME"]
    assert dumped["page"] == 0
    assert dumped["size"] == 10


def test_activity_log_query_excludes_none_optional_fields():
    dumped = ActivityLogQuery(**_required()).model_dump(  # type: ignore[arg-type]
        by_alias=True,
        exclude_none=True,
    )
    for key in ("fieldName", "fieldValue", "header", "page", "size"):
        assert key not in dumped


def test_activity_log_attribute_model_validate_and_null():
    raw = {
        "isDynamic": False,
        "dataType": "STRING",
        "attrType": "User",
        "name": "USER_NAME",
        "value": "John",
    }
    attr = ActivityLogAttribute.model_validate(raw)
    assert attr.name == "USER_NAME"
    assert attr.value == "John"
    assert attr.data_type == "STRING"
    assert attr.attr_type == "User"
    assert attr.is_dynamic is False

    attr_null = ActivityLogAttribute.model_validate({**raw, "value": None})
    assert attr_null.value is None


def test_activity_log_attribute_is_frozen():
    attr = ActivityLogAttribute.model_validate(
        {
            "isDynamic": False,
            "dataType": "STRING",
            "attrType": "Others",
            "name": "ACTION",
            "value": "View",
        },
    )
    with pytest.raises(Exception):
        attr.name = "CHANGED"  # type: ignore[misc]
