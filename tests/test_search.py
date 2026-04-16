from __future__ import annotations

import pytest
from pydantic import ValidationError

from nextlabs_sdk._cloudaz._search import (
    SavedSearch,
    SavedSearchType,
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
