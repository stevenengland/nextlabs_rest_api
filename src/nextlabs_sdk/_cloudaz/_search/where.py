from __future__ import annotations

from types import MappingProxyType
from typing import cast

from scim2_filter_parser.ast import AttrExpr, Filter, LogExpr
from scim2_filter_parser.lexer import SCIMLexer
from scim2_filter_parser.parser import SCIMParser, SCIMParserError

from nextlabs_sdk._cloudaz._search.criteria import SearchField, SearchFieldType
from nextlabs_sdk.exceptions import SearchExpressionError

_STRING_LABEL = "String"

_SCALAR_TYPES: MappingProxyType[str, SearchFieldType] = MappingProxyType(
    {
        "eq": SearchFieldType.SINGLE_EXACT_MATCH,
        "co": SearchFieldType.SINGLE_EXACT_MATCH,
        "sw": SearchFieldType.SINGLE,
    },
)

_OR_GROUP_TYPES: MappingProxyType[str, SearchFieldType] = MappingProxyType(
    {
        "eq": SearchFieldType.MULTI_EXACT_MATCH,
        "co": SearchFieldType.MULTI,
    },
)


def transpile_where(expr: str) -> list[SearchField]:
    """Transpile a SCIM ``--where`` filter into a list of search fields.

    The supported subset is scalar ``eq``/``co``/``sw`` comparisons,
    ``and``-chaining (each term becomes its own field), and same-field
    parenthesised ``or`` groups (a single list-valued field). Cross-field
    ``or`` and any ``not`` are rejected as out of scope for a single
    search request.

    Args:
        expr: The raw SCIM filter string.

    Returns:
        The transpiled search fields, one entry per ``and``-chained term.

    Raises:
        SearchExpressionError: If the filter is malformed, uses an
            unsupported operator, or mixes fields across an ``or``/``not``.
    """
    return _transpile_filter(_parse(expr))


def _parse(expr: str) -> Filter:
    try:
        tree = SCIMParser().parse(SCIMLexer().tokenize(expr))
    except (SCIMParserError, ValueError) as exc:
        raise SearchExpressionError(
            f"could not parse --where filter: {expr!r}",
        ) from exc
    return cast(Filter, tree)


def _transpile_filter(node: Filter) -> list[SearchField]:
    if node.negated:
        raise _cross_field_error()
    inner = node.expr
    if isinstance(inner, Filter):
        return _transpile_filter(inner)
    if isinstance(inner, AttrExpr):
        return [_scalar_field(inner)]
    if isinstance(inner, LogExpr):
        return _transpile_log(inner)
    raise SearchExpressionError("unsupported --where expression")


def _transpile_log(node: LogExpr) -> list[SearchField]:
    operator = node.op.lower()
    if operator == "and":
        return _transpile_filter(node.expr1) + _transpile_filter(node.expr2)
    if operator == "or":
        return [_or_group_field(node)]
    raise _cross_field_error()


def _or_group_field(node: LogExpr) -> SearchField:
    terms = _flatten_or(node)
    names = {term.attr_path.attr_name for term in terms}
    if len(names) != 1:
        raise _cross_field_error()
    if any(term.attr_path.sub_attr is not None for term in terms):
        raise SearchExpressionError(
            "nested attributes are not supported in --where",
        )
    operators = {term.value.lower() for term in terms}
    if len(operators) != 1:
        raise SearchExpressionError(
            "an --where or-group must use a single operator",
        )
    field_type = _or_group_type(next(iter(operators)))
    return SearchField(
        field=next(iter(names)),
        type=field_type,
        value={
            "type": _STRING_LABEL,
            "value": [term.comp_value.value for term in terms],
        },
    )


def _flatten_or(node: LogExpr) -> list[AttrExpr]:
    return _flatten_or_side(node.expr1) + _flatten_or_side(node.expr2)


def _flatten_or_side(node: Filter) -> list[AttrExpr]:
    if node.negated:
        raise _cross_field_error()
    inner = node.expr
    if isinstance(inner, Filter):
        return _flatten_or_side(inner)
    if isinstance(inner, AttrExpr):
        return [inner]
    if isinstance(inner, LogExpr) and inner.op.lower() == "or":
        return _flatten_or(inner)
    raise _cross_field_error()


def _or_group_type(operator: str) -> SearchFieldType:
    try:
        return _OR_GROUP_TYPES[operator]
    except KeyError:
        raise SearchExpressionError(
            f"unsupported --where or-group operator: {operator!r}",
        ) from None


def _scalar_field(node: AttrExpr) -> SearchField:
    name = _attr_name(node)
    field_type = _scalar_types(node)
    return SearchField(
        field=name,
        type=field_type,
        value={"type": _STRING_LABEL, "value": node.comp_value.value},
    )


def _attr_name(node: AttrExpr) -> str:
    if node.attr_path.sub_attr is not None:
        raise SearchExpressionError(
            "nested attributes are not supported in --where",
        )
    return node.attr_path.attr_name


def _scalar_types(node: AttrExpr) -> SearchFieldType:
    operator = node.value.lower()
    try:
        return _SCALAR_TYPES[operator]
    except KeyError:
        raise SearchExpressionError(
            f"unsupported --where operator: {operator!r}",
        ) from None


def _cross_field_error() -> SearchExpressionError:
    return SearchExpressionError(
        "cross-field 'or'/'not' is unsupported in --where; "
        "run separate searches instead",
    )
