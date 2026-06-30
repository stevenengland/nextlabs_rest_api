from __future__ import annotations

from types import MappingProxyType
from typing import Any, cast

from scim2_filter_parser.ast import AttrExpr, AttrPath, Filter, LogExpr
from scim2_filter_parser.lexer import SCIMLexer
from scim2_filter_parser.parser import SCIMParser, SCIMParserError

from nextlabs_sdk._cloudaz._search.criteria import SearchField, SearchFieldType
from nextlabs_sdk._cloudaz._search.dates import (
    DATE_KEYWORDS,
    date_value,
    epoch_millis,
)
from nextlabs_sdk._cloudaz._search.payloads import (
    date_payload,
    string_payload,
    text_payload,
)
from nextlabs_sdk.exceptions import SearchExpressionError

_TEXT_ATTR = "text"
_FROM_DATE = "fromDate"
_TO_DATE = "toDate"
_VALUE_KEY = "value"

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

_DATE_BOUND_KEYS: MappingProxyType[str, str] = MappingProxyType(
    {
        "ge": _FROM_DATE,
        "gt": _FROM_DATE,
        "le": _TO_DATE,
        "lt": _TO_DATE,
    },
)


def transpile_where(expr: str) -> list[SearchField]:
    """Transpile a SCIM ``--where`` filter into a list of search fields.

    The supported subset is scalar ``eq``/``co``/``sw`` comparisons, the
    reserved ``text`` attribute, ``ge``/``gt``/``le``/``lt`` date bounds and
    date keywords, SCIM nested-attribute groupings (``attr[sub op val]``),
    ``and``-chaining (each term becomes its own field), and same-field
    parenthesised ``or`` groups (a single list-valued field). Cross-field
    ``or`` and any ``not`` are rejected as out of scope for a single
    search request.

    Args:
        expr: The raw SCIM filter string.

    Returns:
        The transpiled search fields. Same-field date bounds collapse into a
        single ``DATE`` window; every other term yields its own entry.

    Raises:
        SearchExpressionError: If the filter is malformed, uses an
            unsupported operator, or mixes fields across an ``or``/``not``.
    """
    return _merge_date_windows(_transpile_filter(_parse(expr)))


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
        if inner.namespace is not None:
            return [_nested_field(inner)]
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


def _nested_field(node: Filter) -> SearchField:
    namespace = cast(AttrPath, node.namespace)
    base = namespace.attr_name
    terms = _flatten_or_side(cast(Filter, node.expr))
    sub_names = {term.attr_path.attr_name for term in terms}
    if len(sub_names) != 1:
        raise SearchExpressionError(
            "a nested --where group must target a single sub-attribute",
        )
    nested_field = f"{base}.{next(iter(sub_names))}"
    comp_values = [term.comp_value.value for term in terms]
    if len(terms) == 1:
        return SearchField(
            field=base,
            type=SearchFieldType.NESTED,
            value=string_payload(comp_values[0]),
            nestedField=nested_field,
        )
    return SearchField(
        field=base,
        type=SearchFieldType.NESTED_MULTI,
        value=string_payload(comp_values),
        nestedField=nested_field,
    )


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
        value=string_payload([term.comp_value.value for term in terms]),
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
    operator = node.value.lower()
    comp_value = node.comp_value.value
    if operator in _DATE_BOUND_KEYS:
        return _date_bound_field(name, operator, comp_value)
    if comp_value.upper() in DATE_KEYWORDS:
        return _date_keyword_field(name, comp_value)
    if name == _TEXT_ATTR:
        return _text_field(name, comp_value)
    return SearchField(
        field=name,
        type=_scalar_types(operator),
        value=string_payload(comp_value),
    )


def _date_bound_field(
    name: str,
    operator: str,
    comp_value: str,
) -> SearchField:
    return SearchField(
        field=name,
        type=SearchFieldType.DATE,
        value=date_payload(**{_DATE_BOUND_KEYS[operator]: epoch_millis(comp_value)}),
    )


def _date_keyword_field(name: str, comp_value: str) -> SearchField:
    return SearchField(
        field=name,
        type=SearchFieldType.DATE,
        value=date_value(comp_value),
    )


def _text_field(name: str, comp_value: str) -> SearchField:
    return SearchField(
        field=name,
        type=SearchFieldType.TEXT,
        value=text_payload(comp_value),
    )


def _merge_date_windows(fields: list[SearchField]) -> list[SearchField]:
    merged: list[SearchField] = []
    bound_index: dict[str, int] = {}
    for field in fields:
        if _is_date_window_bound(field) and field.field in bound_index:
            target = merged[bound_index[field.field]]
            combined: dict[str, Any] = dict(target.value)
            combined.update(field.value)
            merged[bound_index[field.field]] = target.model_copy(
                update={_VALUE_KEY: combined},
            )
            continue
        if _is_date_window_bound(field):
            bound_index[field.field] = len(merged)
        merged.append(field)
    return merged


def _is_date_window_bound(field: SearchField) -> bool:
    return field.type is SearchFieldType.DATE and (
        _FROM_DATE in field.value or _TO_DATE in field.value
    )


def _attr_name(node: AttrExpr) -> str:
    if node.attr_path.sub_attr is not None:
        raise SearchExpressionError(
            "nested attributes are not supported in --where",
        )
    return node.attr_path.attr_name


def _scalar_types(operator: str) -> SearchFieldType:
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
