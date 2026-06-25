from __future__ import annotations

import pytest

from nextlabs_sdk._cloudaz._search import SearchFieldType
from nextlabs_sdk._cloudaz._search.field_expr import parse_field_expr
from nextlabs_sdk.exceptions import SearchExpressionError


def test_scalar_value_infers_single_exact_match():
    # given a bare NAME=VALUE with no type and no comma
    expr = "status=DRAFT"

    # when the expression is parsed
    parsed = parse_field_expr(expr)

    # then it carries a SINGLE_EXACT_MATCH field with a scalar value
    assert parsed.field == "status"
    assert parsed.type == SearchFieldType.SINGLE_EXACT_MATCH
    assert parsed.value == {"type": "String", "value": "DRAFT"}


def test_comma_value_infers_multi_list():
    # given a value containing a comma
    expr = "status=DRAFT,APPROVED"

    # when the expression is parsed
    parsed = parse_field_expr(expr)

    # then the type is inferred as MULTI and the value is a list
    assert parsed.type == SearchFieldType.MULTI
    assert parsed.value == {"type": "String", "value": ["DRAFT", "APPROVED"]}


@pytest.mark.parametrize(
    "expr,expected_type",
    [
        pytest.param("status:MULTI=DRAFT", SearchFieldType.MULTI, id="multi"),
        pytest.param(
            "effectType:MULTI_EXACT_MATCH=ALLOW",
            SearchFieldType.MULTI_EXACT_MATCH,
            id="multi-exact-match",
        ),
        pytest.param("name:SINGLE=Allow", SearchFieldType.SINGLE, id="single"),
    ],
)
def test_explicit_type_overrides_inference(
    expr: str,
    expected_type: SearchFieldType,
):
    # given an expression with an explicit :TYPE token
    # when the expression is parsed
    parsed = parse_field_expr(expr)

    # then the explicit type wins over what inference would have chosen
    assert parsed.type == expected_type


def test_explicit_type_is_case_insensitive():
    # given an explicit type token in lower case
    expr = "status:multi=DRAFT"

    # when the expression is parsed
    parsed = parse_field_expr(expr)

    # then the token resolves to the matching SearchFieldType member
    assert parsed.type == SearchFieldType.MULTI


def test_unknown_type_token_raises_search_expression_error():
    # given an expression with an unknown :TYPE token
    expr = "status:BOGUS=DRAFT"

    # when the expression is parsed
    # then a SearchExpressionError is raised
    with pytest.raises(SearchExpressionError):
        parse_field_expr(expr)


def test_missing_assignment_raises_search_expression_error():
    # given an expression without an = assignment
    expr = "status"

    # when the expression is parsed
    # then a SearchExpressionError is raised
    with pytest.raises(SearchExpressionError):
        parse_field_expr(expr)


def test_dotted_name_infers_nested_field():
    # given a dotted NAME with a scalar value
    expr = "tags.key=helpdesk"

    # when the expression is parsed
    parsed = parse_field_expr(expr)

    # then it is a NESTED field whose nestedField is the full dotted path
    assert parsed.type == SearchFieldType.NESTED
    assert parsed.field == "tags"
    assert parsed.nested_field == "tags.key"
    assert parsed.value == {"type": "String", "value": "helpdesk"}


def test_dotted_name_with_comma_infers_nested_multi():
    # given a dotted NAME with a comma-separated value
    expr = "tags.key=helpdesk,billing"

    # when the expression is parsed
    parsed = parse_field_expr(expr)

    # then the type is NESTED_MULTI and the value is a list
    assert parsed.type == SearchFieldType.NESTED_MULTI
    assert parsed.field == "tags"
    assert parsed.nested_field == "tags.key"
    assert parsed.value == {"type": "String", "value": ["helpdesk", "billing"]}


def test_date_keyword_builds_date_option():
    # given an explicit DATE type with a keyword value
    expr = "lastUpdatedDate:DATE=PAST_7_DAYS"

    # when the expression is parsed
    parsed = parse_field_expr(expr)

    # then it carries a DATE field with the keyword as dateOption
    assert parsed.field == "lastUpdatedDate"
    assert parsed.type == SearchFieldType.DATE
    assert parsed.value == {"type": "Date", "dateOption": "PAST_7_DAYS"}


def test_date_range_builds_epoch_millisecond_bounds():
    # given an explicit DATE type with a from..to ISO range
    expr = "lastUpdatedDate:DATE=2024-01-01..2024-02-01"

    # when the expression is parsed
    parsed = parse_field_expr(expr)

    # then the bounds become epoch-millisecond fromDate/toDate
    assert parsed.type == SearchFieldType.DATE
    assert parsed.value == {
        "type": "Date",
        "fromDate": 1704067200000,
        "toDate": 1706745600000,
    }


def test_malformed_date_value_raises_search_expression_error():
    # given an explicit DATE type with an unparseable value
    expr = "lastUpdatedDate:DATE=BOGUS"

    # when the expression is parsed
    # then a SearchExpressionError is raised
    with pytest.raises(SearchExpressionError):
        parse_field_expr(expr)


def test_text_type_builds_default_subfields():
    # given the reserved text attribute with an explicit TEXT type
    expr = "text:TEXT=ticket"

    # when the expression is parsed
    parsed = parse_field_expr(expr)

    # then it is a TEXT entry carrying the default name/description subfields
    assert parsed.field == "text"
    assert parsed.type == SearchFieldType.TEXT
    assert parsed.value == {
        "type": "Text",
        "fields": ["name", "description"],
        "value": "ticket",
    }
