from __future__ import annotations

from typing import Any

from nextlabs_sdk._cloudaz._search.criteria import SearchField, SearchFieldType
from nextlabs_sdk._cloudaz._search.dates import date_value
from nextlabs_sdk.exceptions import SearchExpressionError

_STRING_LABEL = "String"
_TEXT_LABEL = "Text"
_TEXT_DEFAULT_FIELDS = ("name", "description")


def parse_field_expr(expr: str) -> SearchField:
    """Parse a ``NAME[:TYPE]=VALUE`` field expression into a search field.

    The match type is taken from an explicit ``:TYPE`` token when present
    (case-insensitive), otherwise inferred: a dotted ``NAME`` yields a
    ``NESTED`` (``NESTED_MULTI`` with a comma) field, a comma in the value
    yields a ``MULTI`` list, a bare value yields ``SINGLE_EXACT_MATCH``.

    A dotted ``NAME`` sets ``field`` to the segment before the last dot and
    ``nested_field`` to the full dotted path. A ``DATE`` value is a keyword or
    a ``from..to`` ISO range; the reserved ``TEXT`` type carries default
    ``name``/``description`` subfields.

    Args:
        expr: The raw ``NAME[:TYPE]=VALUE`` expression.

    Returns:
        The parsed search field.

    Raises:
        SearchExpressionError: If the expression lacks an assignment, carries
            an unknown type token, or holds a malformed date value.
    """
    name_part, sep, raw_value = expr.partition("=")
    if not sep:
        raise SearchExpressionError(
            f"field expression must be NAME[:TYPE]=VALUE: {expr!r}",
        )

    name, type_token = _split_name(name_part)
    field, nested_field = _resolve_field(name)
    is_list = "," in raw_value
    field_type = _resolve_type(
        type_token,
        is_list=is_list,
        is_nested=nested_field is not None,
    )
    payload = _value_payload(raw_value, field_type, is_list=is_list)
    return SearchField(
        field=field,
        type=field_type,
        value=payload,
        nestedField=nested_field,
    )


def _split_name(name_part: str) -> tuple[str, str | None]:
    name, sep, type_token = name_part.partition(":")
    if not name:
        raise SearchExpressionError("field expression is missing a NAME")
    return name, type_token if sep else None


def _resolve_field(name: str) -> tuple[str, str | None]:
    if "." not in name:
        return name, None
    base, _, _leaf = name.rpartition(".")
    return base, name


def _resolve_type(
    type_token: str | None,
    *,
    is_list: bool,
    is_nested: bool,
) -> SearchFieldType:
    if type_token is not None:
        return _explicit_type(type_token)
    if is_nested:
        return SearchFieldType.NESTED_MULTI if is_list else SearchFieldType.NESTED
    return SearchFieldType.MULTI if is_list else SearchFieldType.SINGLE_EXACT_MATCH


def _explicit_type(type_token: str) -> SearchFieldType:
    try:
        return SearchFieldType[type_token.strip().upper()]
    except KeyError:
        raise SearchExpressionError(
            f"unknown field type token: {type_token!r}",
        ) from None


def _value_payload(
    raw_value: str,
    field_type: SearchFieldType,
    *,
    is_list: bool,
) -> dict[str, Any]:
    if field_type is SearchFieldType.DATE:
        return date_value(raw_value)
    if field_type is SearchFieldType.TEXT:
        return {
            "type": _TEXT_LABEL,
            "fields": list(_TEXT_DEFAULT_FIELDS),
            "value": raw_value,
        }
    if is_list:
        parsed: object = [part.strip() for part in raw_value.split(",")]
    else:
        parsed = raw_value
    return {"type": _STRING_LABEL, "value": parsed}
