from __future__ import annotations

import pytest
from pydantic import ValidationError

from nextlabs_sdk._cloudaz._search import (
    SavedSearch,
    SavedSearchType,
    SearchCriteria,
    SearchField,
    SearchFieldType,
    SortField,
    SortOrder,
)


def test_search_field_type_values() -> None:
    assert SearchFieldType.SINGLE.value == "SINGLE"
    assert SearchFieldType.MULTI_EXACT_MATCH.value == "MULTI_EXACT_MATCH"
    assert SearchFieldType.NESTED_MULTI.value == "NESTED_MULTI"
    assert SearchFieldType.TEXT.value == "TEXT"
    assert SearchFieldType.DATE.value == "DATE"


def test_sort_order_values() -> None:
    assert SortOrder.ASC.value == "ASC"
    assert SortOrder.DESC.value == "DESC"


def test_sort_field_from_api_payload() -> None:
    raw = {"field": "lastUpdatedDate", "order": "DESC"}
    sf = SortField.model_validate(raw)
    assert sf.field == "lastUpdatedDate"
    assert sf.order == SortOrder.DESC


def test_sort_field_is_frozen() -> None:
    sf = SortField(field="name", order=SortOrder.ASC)
    with pytest.raises(ValidationError):
        sf.field = "changed"  # type: ignore[misc]


def test_search_field_from_api_payload() -> None:
    raw = {
        "field": "type",
        "type": "MULTI_EXACT_MATCH",
        "value": {"type": "String", "value": ["RESOURCE"]},
    }
    sf = SearchField.model_validate(raw)
    assert sf.field == "type"
    assert sf.type == SearchFieldType.MULTI_EXACT_MATCH
    assert sf.nested_field is None


def test_search_field_with_nested_field() -> None:
    raw = {
        "field": "tags",
        "nestedField": "tags.key",
        "type": "NESTED_MULTI",
        "value": {"type": "String", "value": ["helpdesk"]},
    }
    sf = SearchField.model_validate(raw)
    assert sf.nested_field == "tags.key"


def test_search_field_is_frozen() -> None:
    sf = SearchField(
        field="type",
        type=SearchFieldType.SINGLE,
        value={"type": "String", "value": "RESOURCE"},
    )
    with pytest.raises(ValidationError):
        sf.field = "changed"  # type: ignore[misc]


def test_saved_search_type_values() -> None:
    assert SavedSearchType.COMPONENT.value == "COMPONENT"
    assert SavedSearchType.POLICY.value == "POLICY"
    assert SavedSearchType.POLICY_MODEL_RESOURCE.value == "POLICY_MODEL_RESOURCE"
    assert SavedSearchType.POLICY_MODEL_SUBJECT.value == "POLICY_MODEL_SUBJECT"


def test_saved_search_from_api_payload() -> None:
    raw = {
        "id": 42,
        "name": "My Search",
        "desc": "A saved search",
        "type": "POLICY_MODEL_RESOURCE",
        "status": "ACTIVE",
        "sharedMode": "PUBLIC",
        "criteria": {"fields": [], "pageNo": 0, "pageSize": 20},
    }
    ss = SavedSearch.model_validate(raw)
    assert ss.id == 42
    assert ss.name == "My Search"
    assert ss.desc == "A saved search"
    assert ss.type == SavedSearchType.POLICY_MODEL_RESOURCE
    assert ss.status == "ACTIVE"
    assert ss.shared_mode == "PUBLIC"
    assert ss.criteria is not None


def test_saved_search_optional_fields() -> None:
    raw = {
        "id": 1,
        "name": "Minimal",
        "type": "COMPONENT",
    }
    ss = SavedSearch.model_validate(raw)
    assert ss.desc is None
    assert ss.status is None
    assert ss.shared_mode is None
    assert ss.criteria is None


def test_saved_search_is_frozen() -> None:
    ss = SavedSearch(id=1, name="test", type=SavedSearchType.POLICY)
    with pytest.raises(ValidationError):
        ss.name = "changed"  # type: ignore[misc]


def test_search_criteria_empty() -> None:
    criteria = SearchCriteria()
    result = criteria.to_dict()
    assert result == {
        "criteria": {
            "fields": [],
            "sortFields": [],
            "pageNo": 0,
            "pageSize": 20,
        },
    }


def test_search_criteria_filter_type_single() -> None:
    criteria = SearchCriteria().filter_type("RESOURCE")
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == "type"
    assert fields[0]["type"] == "MULTI_EXACT_MATCH"
    assert fields[0]["value"] == {"type": "String", "value": ["RESOURCE"]}


def test_search_criteria_filter_type_multiple() -> None:
    criteria = SearchCriteria().filter_type("RESOURCE", "SUBJECT")
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert fields[0]["value"]["value"] == ["RESOURCE", "SUBJECT"]


def test_search_criteria_filter_tags() -> None:
    criteria = SearchCriteria().filter_tags("helpdesk", "ops")
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == "tags"
    assert fields[0]["nestedField"] == "tags.key"
    assert fields[0]["type"] == "NESTED_MULTI"
    assert fields[0]["value"] == {"type": "String", "value": ["helpdesk", "ops"]}


def test_search_criteria_filter_text_default_fields() -> None:
    criteria = SearchCriteria().filter_text("support")
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == "text"
    assert fields[0]["type"] == "TEXT"
    assert fields[0]["value"] == {
        "type": "Text",
        "fields": ["name", "description"],
        "value": "support",
    }


def test_search_criteria_filter_text_custom_fields() -> None:
    criteria = SearchCriteria().filter_text("ticket", fields=["name"])
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert fields[0]["value"]["fields"] == ["name"]


def test_search_criteria_filter_date_range() -> None:
    criteria = SearchCriteria().filter_date(
        "lastUpdatedDate",
        from_date=1000,
        to_date=2000,
    )
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == "lastUpdatedDate"
    assert fields[0]["type"] == "DATE"
    assert fields[0]["value"]["type"] == "Date"
    assert fields[0]["value"]["fromDate"] == 1000
    assert fields[0]["value"]["toDate"] == 2000


def test_search_criteria_filter_date_option() -> None:
    criteria = SearchCriteria().filter_date(
        "lastUpdatedDate",
        date_option="PAST_7_DAYS",
    )
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert fields[0]["value"]["dateOption"] == "PAST_7_DAYS"


def test_search_criteria_filter_field_raw() -> None:
    raw_field = SearchField(
        field="status",
        type=SearchFieldType.SINGLE_EXACT_MATCH,
        value={"type": "String", "value": "ACTIVE"},
    )
    criteria = SearchCriteria().filter_field(raw_field)
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == "status"


def test_search_criteria_sort_by() -> None:
    criteria = SearchCriteria().sort_by("lastUpdatedDate", SortOrder.DESC)
    result = criteria.to_dict()
    sort_fields = result["criteria"]["sortFields"]
    assert len(sort_fields) == 1
    assert sort_fields[0] == {"field": "lastUpdatedDate", "order": "DESC"}


def test_search_criteria_page() -> None:
    criteria = SearchCriteria().page(3, 50)
    result = criteria.to_dict()
    assert result["criteria"]["pageNo"] == 3
    assert result["criteria"]["pageSize"] == 50


def test_search_criteria_chaining() -> None:
    criteria = (
        SearchCriteria()
        .filter_type("RESOURCE")
        .filter_tags("helpdesk")
        .sort_by("lastUpdatedDate")
        .page(0, 10)
    )
    result = criteria.to_dict()
    assert len(result["criteria"]["fields"]) == 2
    assert len(result["criteria"]["sortFields"]) == 1
    assert result["criteria"]["pageNo"] == 0
    assert result["criteria"]["pageSize"] == 10


def test_search_criteria_filter_group() -> None:
    criteria = SearchCriteria().filter_group("RESOURCE")
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == "group"
    assert fields[0]["type"] == "SINGLE_EXACT_MATCH"
    assert fields[0]["value"] == {"type": "String", "value": "RESOURCE"}


def test_search_criteria_filter_status_single() -> None:
    criteria = SearchCriteria().filter_status("APPROVED")
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == "status"
    assert fields[0]["type"] == "MULTI"
    assert fields[0]["value"] == {"type": "String", "value": ["APPROVED"]}


def test_search_criteria_filter_status_multiple() -> None:
    criteria = SearchCriteria().filter_status("DRAFT", "APPROVED")
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert fields[0]["value"]["value"] == ["DRAFT", "APPROVED"]


def test_search_criteria_filter_model_type() -> None:
    criteria = SearchCriteria().filter_model_type("Support Tickets")
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == "modelType"
    assert fields[0]["type"] == "MULTI"
    assert fields[0]["value"] == {"type": "String", "value": ["Support Tickets"]}


def test_search_criteria_filter_model_type_multiple() -> None:
    criteria = SearchCriteria().filter_model_type("Support Tickets", "Users")
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert fields[0]["value"]["value"] == ["Support Tickets", "Users"]


def test_search_criteria_filter_exact() -> None:
    criteria = SearchCriteria().filter_exact("empty", "false")
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == "empty"
    assert fields[0]["type"] == "SINGLE_EXACT_MATCH"
    assert fields[0]["value"] == {"type": "String", "value": "false"}


def test_search_criteria_filter_exact_has_included_in() -> None:
    criteria = SearchCriteria().filter_exact("hasIncludedIn", "true")
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert fields[0]["field"] == "hasIncludedIn"
    assert fields[0]["value"]["value"] == "true"


def test_search_criteria_component_chaining() -> None:
    criteria = (
        SearchCriteria()
        .filter_group("RESOURCE")
        .filter_status("APPROVED")
        .filter_tags("helpdesk")
        .sort_by("lastUpdatedDate")
    )
    result = criteria.to_dict()
    assert len(result["criteria"]["fields"]) == 3
    assert len(result["criteria"]["sortFields"]) == 1


def test_search_criteria_filter_effect_type_single() -> None:
    criteria = SearchCriteria().filter_effect_type("allow")
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == "effectType"
    assert fields[0]["type"] == "MULTI_EXACT_MATCH"
    assert fields[0]["value"] == {"type": "String", "value": ["allow"]}


def test_search_criteria_filter_effect_type_multiple() -> None:
    criteria = SearchCriteria().filter_effect_type("allow", "deny")
    result = criteria.to_dict()
    fields = result["criteria"]["fields"]
    assert fields[0]["value"]["value"] == ["allow", "deny"]


def test_search_criteria_policy_chaining() -> None:
    criteria = (
        SearchCriteria()
        .filter_effect_type("allow")
        .filter_status("DRAFT")
        .filter_tags("helpdesk")
    )
    result = criteria.to_dict()
    assert len(result["criteria"]["fields"]) == 3
