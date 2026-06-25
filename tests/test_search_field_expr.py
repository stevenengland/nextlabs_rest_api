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
