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


@pytest.mark.parametrize(
    "member,expected",
    [
        pytest.param(SearchFieldType.SINGLE, "SINGLE", id="single"),
        pytest.param(
            SearchFieldType.MULTI_EXACT_MATCH,
            "MULTI_EXACT_MATCH",
            id="multi-exact-match",
        ),
        pytest.param(SearchFieldType.NESTED_MULTI, "NESTED_MULTI", id="nested-multi"),
        pytest.param(SearchFieldType.TEXT, "TEXT", id="text"),
        pytest.param(SearchFieldType.DATE, "DATE", id="date"),
        pytest.param(SortOrder.ASC, "ASC", id="sort-asc"),
        pytest.param(SortOrder.DESC, "DESC", id="sort-desc"),
        pytest.param(SavedSearchType.COMPONENT, "COMPONENT", id="saved-component"),
        pytest.param(SavedSearchType.POLICY, "POLICY", id="saved-policy"),
        pytest.param(
            SavedSearchType.POLICY_MODEL_RESOURCE,
            "POLICY_MODEL_RESOURCE",
            id="saved-policy-model-resource",
        ),
        pytest.param(
            SavedSearchType.POLICY_MODEL_SUBJECT,
            "POLICY_MODEL_SUBJECT",
            id="saved-policy-model-subject",
        ),
    ],
)
def test_enum_values(member, expected):
    assert member.value == expected


def test_sort_field_from_api_payload():
    sf = SortField.model_validate({"field": "lastUpdatedDate", "order": "DESC"})
    assert sf.field == "lastUpdatedDate"
    assert sf.order == SortOrder.DESC


def test_search_field_from_api_payload():
    sf = SearchField.model_validate(
        {
            "field": "type",
            "type": "MULTI_EXACT_MATCH",
            "value": {"type": "String", "value": ["RESOURCE"]},
        }
    )
    assert sf.field == "type"
    assert sf.type == SearchFieldType.MULTI_EXACT_MATCH
    assert sf.nested_field is None


def test_search_field_with_nested_field():
    sf = SearchField.model_validate(
        {
            "field": "tags",
            "nestedField": "tags.key",
            "type": "NESTED_MULTI",
            "value": {"type": "String", "value": ["helpdesk"]},
        }
    )
    assert sf.nested_field == "tags.key"


@pytest.mark.parametrize(
    "build_instance,attr,new_value",
    [
        pytest.param(
            lambda: SortField(field="name", order=SortOrder.ASC),
            "field",
            "changed",
            id="sort-field",
        ),
        pytest.param(
            lambda: SearchField(
                field="type",
                type=SearchFieldType.SINGLE,
                value={"type": "String", "value": "RESOURCE"},
            ),
            "field",
            "changed",
            id="search-field",
        ),
        pytest.param(
            lambda: SavedSearch(id=1, name="test", type=SavedSearchType.POLICY),
            "name",
            "changed",
            id="saved-search",
        ),
    ],
)
def test_models_are_frozen(build_instance, attr, new_value):
    instance = build_instance()
    with pytest.raises(ValidationError):
        setattr(instance, attr, new_value)


def test_saved_search_from_api_payload():
    ss = SavedSearch.model_validate(
        {
            "id": 42,
            "name": "My Search",
            "desc": "A saved search",
            "type": "POLICY_MODEL_RESOURCE",
            "status": "ACTIVE",
            "sharedMode": "PUBLIC",
            "criteria": {"fields": [], "pageNo": 0, "pageSize": 20},
        }
    )
    assert ss.id == 42
    assert ss.name == "My Search"
    assert ss.desc == "A saved search"
    assert ss.type == SavedSearchType.POLICY_MODEL_RESOURCE
    assert ss.status == "ACTIVE"
    assert ss.shared_mode == "PUBLIC"
    assert ss.criteria is not None


def test_saved_search_optional_fields():
    ss = SavedSearch.model_validate({"id": 1, "name": "Minimal", "type": "COMPONENT"})
    assert ss.desc is None
    assert ss.status is None
    assert ss.shared_mode is None
    assert ss.criteria is None


def test_search_criteria_empty():
    assert SearchCriteria().to_dict() == {
        "criteria": {
            "fields": [],
            "sortFields": [],
            "pageNo": 0,
            "pageSize": 20,
        },
    }


@pytest.mark.parametrize(
    "method,args,expected_field,expected_type",
    [
        pytest.param(
            "filter_type",
            ("RESOURCE",),
            "type",
            "MULTI_EXACT_MATCH",
            id="filter-type-single",
        ),
        pytest.param(
            "filter_effect_type",
            ("allow",),
            "effectType",
            "MULTI_EXACT_MATCH",
            id="filter-effect-type-single",
        ),
        pytest.param(
            "filter_status", ("APPROVED",), "status", "MULTI", id="filter-status-single"
        ),
        pytest.param(
            "filter_model_type",
            ("Support Tickets",),
            "modelType",
            "MULTI",
            id="filter-model-type-single",
        ),
    ],
)
def test_search_criteria_multi_value_filters_single(
    method,
    args,
    expected_field,
    expected_type,
):
    criteria = getattr(SearchCriteria(), method)(*args)
    fields = criteria.to_dict()["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == expected_field
    assert fields[0]["type"] == expected_type
    assert fields[0]["value"] == {"type": "String", "value": list(args)}


@pytest.mark.parametrize(
    "method,args,expected_values",
    [
        pytest.param(
            "filter_type",
            ("RESOURCE", "SUBJECT"),
            ["RESOURCE", "SUBJECT"],
            id="filter-type-multiple",
        ),
        pytest.param(
            "filter_effect_type",
            ("allow", "deny"),
            ["allow", "deny"],
            id="filter-effect-type-multiple",
        ),
        pytest.param(
            "filter_status",
            ("DRAFT", "APPROVED"),
            ["DRAFT", "APPROVED"],
            id="filter-status-multiple",
        ),
        pytest.param(
            "filter_model_type",
            ("Support Tickets", "Users"),
            ["Support Tickets", "Users"],
            id="filter-model-type-multiple",
        ),
    ],
)
def test_search_criteria_multi_value_filters_multiple(method, args, expected_values):
    criteria = getattr(SearchCriteria(), method)(*args)
    fields = criteria.to_dict()["criteria"]["fields"]
    assert fields[0]["value"]["value"] == expected_values


def test_search_criteria_filter_tags():
    criteria = SearchCriteria().filter_tags("helpdesk", "ops")
    fields = criteria.to_dict()["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == "tags"
    assert fields[0]["nestedField"] == "tags.key"
    assert fields[0]["type"] == "NESTED_MULTI"
    assert fields[0]["value"] == {"type": "String", "value": ["helpdesk", "ops"]}


def test_search_criteria_filter_text_default_fields():
    criteria = SearchCriteria().filter_text("support")
    fields = criteria.to_dict()["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == "text"
    assert fields[0]["type"] == "TEXT"
    assert fields[0]["value"] == {
        "type": "Text",
        "fields": ["name", "description"],
        "value": "support",
    }


def test_search_criteria_filter_text_custom_fields():
    criteria = SearchCriteria().filter_text("ticket", fields=["name"])
    fields = criteria.to_dict()["criteria"]["fields"]
    assert fields[0]["value"]["fields"] == ["name"]


def test_search_criteria_filter_date_range():
    criteria = SearchCriteria().filter_date(
        "lastUpdatedDate",
        from_date=1000,
        to_date=2000,
    )
    fields = criteria.to_dict()["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == "lastUpdatedDate"
    assert fields[0]["type"] == "DATE"
    assert fields[0]["value"]["type"] == "Date"
    assert fields[0]["value"]["fromDate"] == 1000
    assert fields[0]["value"]["toDate"] == 2000


def test_search_criteria_filter_date_option():
    criteria = SearchCriteria().filter_date(
        "lastUpdatedDate",
        date_option="PAST_7_DAYS",
    )
    fields = criteria.to_dict()["criteria"]["fields"]
    assert fields[0]["value"]["dateOption"] == "PAST_7_DAYS"


def test_search_criteria_filter_field_raw():
    raw_field = SearchField(
        field="status",
        type=SearchFieldType.SINGLE_EXACT_MATCH,
        value={"type": "String", "value": "ACTIVE"},
    )
    criteria = SearchCriteria().filter_field(raw_field)
    fields = criteria.to_dict()["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == "status"


def test_search_criteria_sort_by():
    criteria = SearchCriteria().sort_by("lastUpdatedDate", SortOrder.DESC)
    sort_fields = criteria.to_dict()["criteria"]["sortFields"]
    assert len(sort_fields) == 1
    assert sort_fields[0] == {"field": "lastUpdatedDate", "order": "DESC"}


def test_search_criteria_page():
    result = SearchCriteria().page(3, 50).to_dict()
    assert result["criteria"]["pageNo"] == 3
    assert result["criteria"]["pageSize"] == 50


def test_search_criteria_chaining():
    result = (
        SearchCriteria()
        .filter_type("RESOURCE")
        .filter_tags("helpdesk")
        .sort_by("lastUpdatedDate")
        .page(0, 10)
    ).to_dict()
    assert len(result["criteria"]["fields"]) == 2
    assert len(result["criteria"]["sortFields"]) == 1
    assert result["criteria"]["pageNo"] == 0
    assert result["criteria"]["pageSize"] == 10


def test_search_criteria_filter_group():
    fields = SearchCriteria().filter_group("RESOURCE").to_dict()["criteria"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field"] == "group"
    assert fields[0]["type"] == "SINGLE_EXACT_MATCH"
    assert fields[0]["value"] == {"type": "String", "value": "RESOURCE"}


def test_search_criteria_filter_exact():
    fields = (
        SearchCriteria().filter_exact("empty", "false").to_dict()["criteria"]["fields"]
    )
    assert len(fields) == 1
    assert fields[0]["field"] == "empty"
    assert fields[0]["type"] == "SINGLE_EXACT_MATCH"
    assert fields[0]["value"] == {"type": "String", "value": "false"}


def test_search_criteria_filter_exact_has_included_in():
    fields = (
        SearchCriteria()
        .filter_exact("hasIncludedIn", "true")
        .to_dict()["criteria"]["fields"]
    )
    assert fields[0]["field"] == "hasIncludedIn"
    assert fields[0]["value"]["value"] == "true"


def test_search_criteria_component_chaining():
    result = (
        SearchCriteria()
        .filter_group("RESOURCE")
        .filter_status("APPROVED")
        .filter_tags("helpdesk")
        .sort_by("lastUpdatedDate")
    ).to_dict()
    assert len(result["criteria"]["fields"]) == 3
    assert len(result["criteria"]["sortFields"]) == 1


def test_search_criteria_policy_chaining():
    result = (
        SearchCriteria()
        .filter_effect_type("allow")
        .filter_status("DRAFT")
        .filter_tags("helpdesk")
    ).to_dict()
    assert len(result["criteria"]["fields"]) == 3
