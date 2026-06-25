from __future__ import annotations

import pytest

from nextlabs_sdk._cloudaz._search import SearchFieldType
from nextlabs_sdk._cloudaz._search.where import transpile_where
from nextlabs_sdk.exceptions import SearchExpressionError


def test_scalar_eq_maps_to_single_exact_match():
    # given a scalar eq filter
    where = 'status eq "DRAFT"'

    # when the filter is transpiled
    fields = transpile_where(where)

    # then one SINGLE_EXACT_MATCH field carries the scalar value
    assert len(fields) == 1
    assert fields[0].field == "status"
    assert fields[0].type == SearchFieldType.SINGLE_EXACT_MATCH
    assert fields[0].value == {"type": "String", "value": "DRAFT"}


def test_scalar_co_maps_to_single_exact_match():
    # given a scalar co (contains) filter
    where = 'name co "Allow"'

    # when the filter is transpiled
    fields = transpile_where(where)

    # then it becomes a SINGLE_EXACT_MATCH field
    assert fields[0].field == "name"
    assert fields[0].type == SearchFieldType.SINGLE_EXACT_MATCH
    assert fields[0].value == {"type": "String", "value": "Allow"}


def test_scalar_sw_maps_to_single():
    # given a scalar sw (starts-with) filter
    where = 'name sw "Allow"'

    # when the filter is transpiled
    fields = transpile_where(where)

    # then it becomes a SINGLE (prefix) field
    assert fields[0].field == "name"
    assert fields[0].type == SearchFieldType.SINGLE
    assert fields[0].value == {"type": "String", "value": "Allow"}


def test_and_chain_yields_one_field_per_term():
    # given two terms joined by and
    where = 'status eq "DRAFT" and name co "Allow"'

    # when the filter is transpiled
    fields = transpile_where(where)

    # then both terms AND into the field list, one entry each
    assert len(fields) == 2
    assert {entry.field for entry in fields} == {"status", "name"}


def test_and_chain_of_three_terms_flattens():
    # given three terms joined by and
    where = 'status eq "DRAFT" and effectType eq "ALLOW" and name sw "A"'

    # when the filter is transpiled
    fields = transpile_where(where)

    # then all three terms appear as separate fields
    assert len(fields) == 3
    assert {entry.field for entry in fields} == {
        "status",
        "effectType",
        "name",
    }


def test_unsupported_scalar_operator_raises():
    # given a scalar operator outside the MVP set
    where = 'status pr "x"'

    # when the filter is transpiled
    # then a SearchExpressionError is raised
    with pytest.raises(SearchExpressionError):
        transpile_where(where)


def test_malformed_filter_raises_search_expression_error():
    # given a syntactically invalid filter
    where = "status eq"

    # when the filter is transpiled
    # then the parser failure surfaces as a SearchExpressionError
    with pytest.raises(SearchExpressionError):
        transpile_where(where)


def test_same_field_eq_or_group_maps_to_multi_exact_match():
    # given a same-field paren-OR group of eq terms
    where = '(status eq "DRAFT" or status eq "APPROVED")'

    # when the filter is transpiled
    fields = transpile_where(where)

    # then it becomes one MULTI_EXACT_MATCH list field
    assert len(fields) == 1
    assert fields[0].field == "status"
    assert fields[0].type == SearchFieldType.MULTI_EXACT_MATCH
    assert fields[0].value == {
        "type": "String",
        "value": ["DRAFT", "APPROVED"],
    }


def test_same_field_co_or_group_maps_to_multi():
    # given a same-field paren-OR group of co terms
    where = '(name co "Allow" or name co "Deny")'

    # when the filter is transpiled
    fields = transpile_where(where)

    # then it becomes one MULTI list field
    assert len(fields) == 1
    assert fields[0].field == "name"
    assert fields[0].type == SearchFieldType.MULTI
    assert fields[0].value == {"type": "String", "value": ["Allow", "Deny"]}


def test_three_term_same_field_or_group_collects_all_values():
    # given a three-term same-field eq OR group
    where = '(status eq "DRAFT" or status eq "APPROVED" or status eq "RETIRED")'

    # when the filter is transpiled
    fields = transpile_where(where)

    # then all three values collect into one list field
    assert len(fields) == 1
    assert fields[0].type == SearchFieldType.MULTI_EXACT_MATCH
    assert fields[0].value == {
        "type": "String",
        "value": ["DRAFT", "APPROVED", "RETIRED"],
    }


def test_or_group_anded_with_scalar_term():
    # given a same-field OR group AND-chained with a scalar term
    where = '(status eq "DRAFT" or status eq "APPROVED") and name co "Allow"'

    # when the filter is transpiled
    fields = transpile_where(where)

    # then the group yields a list field and the scalar yields its own field
    assert len(fields) == 2
    by_field = {entry.field: entry for entry in fields}
    assert by_field["status"].type == SearchFieldType.MULTI_EXACT_MATCH
    assert by_field["name"].type == SearchFieldType.SINGLE_EXACT_MATCH


def test_or_group_mixing_operators_raises():
    # given a same-field OR group mixing eq and co operators
    where = '(status eq "DRAFT" or status co "APP")'

    # when the filter is transpiled
    # then a SearchExpressionError is raised
    with pytest.raises(SearchExpressionError):
        transpile_where(where)
