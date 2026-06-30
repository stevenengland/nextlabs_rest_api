from __future__ import annotations

from typing import Any, Sequence

_STRING_LABEL = "String"
_TEXT_LABEL = "Text"
_DATE_LABEL = "Date"
_TEXT_DEFAULT_FIELDS = ("name", "description")

_TYPE_KEY = "type"
_VALUE_KEY = "value"
_FIELDS_KEY = "fields"


def string_payload(value: Any) -> dict[str, Any]:  # noqa: WPS110
    """Encode a ``String`` typed search value (scalar or list)."""
    return {_TYPE_KEY: _STRING_LABEL, _VALUE_KEY: value}


def text_payload(
    value: str,  # noqa: WPS110
    *,
    fields: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Encode a ``Text`` typed search value over the given (or default) fields."""
    subfields = list(fields) if fields else list(_TEXT_DEFAULT_FIELDS)
    return {_TYPE_KEY: _TEXT_LABEL, _FIELDS_KEY: subfields, _VALUE_KEY: value}


def date_payload(**entries: Any) -> dict[str, Any]:
    """Encode a ``Date`` typed search value from the given bound/option entries."""
    return {_TYPE_KEY: _DATE_LABEL, **entries}
