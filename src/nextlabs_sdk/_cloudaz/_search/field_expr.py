from __future__ import annotations

from nextlabs_sdk._cloudaz._search.criteria import SearchField, SearchFieldType
from nextlabs_sdk.exceptions import SearchExpressionError

_STRING_LABEL = "String"


def parse_field_expr(expr: str) -> SearchField:
    """Parse a ``NAME[:TYPE]=VALUE`` field expression into a search field.

    The match type is taken from an explicit ``:TYPE`` token when present
    (case-insensitive), otherwise inferred: a comma in the value yields a
    ``MULTI`` list, a bare value yields ``SINGLE_EXACT_MATCH``.

    Args:
        expr: The raw ``NAME[:TYPE]=VALUE`` expression.

    Returns:
        The parsed search field.

    Raises:
        SearchExpressionError: If the expression lacks an assignment or
            carries an unknown type token.
    """
    name_part, sep, raw_value = expr.partition("=")
    if not sep:
        raise SearchExpressionError(
            f"field expression must be NAME[:TYPE]=VALUE: {expr!r}",
        )

    name, type_token = _split_name(name_part)
    is_list = "," in raw_value
    field_type = _resolve_type(type_token, is_list=is_list)
    payload = _value_payload(raw_value, is_list=is_list)
    return SearchField(field=name, type=field_type, value=payload)


def _split_name(name_part: str) -> tuple[str, str | None]:
    name, sep, type_token = name_part.partition(":")
    if not name:
        raise SearchExpressionError("field expression is missing a NAME")
    return name, type_token if sep else None


def _resolve_type(type_token: str | None, *, is_list: bool) -> SearchFieldType:
    if type_token is None:
        return SearchFieldType.MULTI if is_list else SearchFieldType.SINGLE_EXACT_MATCH
    try:
        return SearchFieldType[type_token.strip().upper()]
    except KeyError:
        raise SearchExpressionError(
            f"unknown field type token: {type_token!r}",
        ) from None


def _value_payload(raw_value: str, *, is_list: bool) -> dict[str, object]:
    if is_list:
        parsed: object = [part.strip() for part in raw_value.split(",")]
    else:
        parsed = raw_value
    return {"type": _STRING_LABEL, "value": parsed}
