"""Parity checks between registered SDK Pydantic DTOs and the vendor OpenAPI spec.

The checks answer three narrow questions about each registered response
triple:

1. Does the SDK's required-field set (Pydantic fields without a default
   value) match the OpenAPI ``required`` list for the inner ``data``
   schema?
2. Is the SDK's property-alias set the same as the OpenAPI
   ``properties`` keyset?
3. For every SDK ``Enum`` field whose OpenAPI counterpart has an
   ``enum`` list, does the SDK enum cover every OpenAPI value?

Each check is a pure function returning a diff (a pair of frozensets —
``only_in_sdk`` and ``only_in_spec``) so the test layer can subtract an
allowlist and decide whether to fail. This module never raises on
drift — the test layer does that — and never mutates the spec dict.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel


class SchemaResolutionError(Exception):
    """Raised when the inner DTO schema cannot be located in the spec."""


@dataclass(frozen=True)
class Diff:
    """Symmetric difference between two named sets.

    ``only_in_sdk`` holds entries the SDK declares that the spec omits;
    ``only_in_spec`` the reverse. Both empty means parity.
    """

    only_in_sdk: frozenset[str]
    only_in_spec: frozenset[str]

    def is_empty(self) -> bool:
        return not self.only_in_sdk and not self.only_in_spec


@dataclass(frozen=True)
class EnumDiff:
    """Missing enum values, per field alias."""

    field: str
    missing_in_sdk: frozenset[str]


def resolve_ref(spec: dict[str, Any], ref: str) -> dict[str, Any]:
    """Follow a ``#/components/schemas/Foo``-style JSON pointer."""
    if not ref.startswith("#/"):
        raise SchemaResolutionError(f"non-local $ref: {ref}")
    node: Any = spec
    for part in ref.removeprefix("#/").split("/"):
        if not isinstance(node, dict) or part not in node:
            raise SchemaResolutionError(f"cannot resolve {ref}")
        node = node[part]
    if not isinstance(node, dict):
        raise SchemaResolutionError(f"{ref} does not resolve to an object")
    return node


def response_schema(
    spec: dict[str, Any],
    path: str,
    method: str,
    status: str,
) -> dict[str, Any]:
    """Return the top-level response schema for a triple, following one $ref."""
    try:
        op = spec["paths"][path][method]
        responses = op["responses"][status]
    except (KeyError, TypeError) as exc:
        raise SchemaResolutionError(
            f"no response for {method.upper()} {path} -> {status}",
        ) from exc
    content = responses.get("content") or {}
    media = content.get("application/json") or content.get("*/*")
    if media is None and content:
        media = next(iter(content.values()))
    if not media:
        raise SchemaResolutionError(
            f"no media for {method.upper()} {path} -> {status}",
        )
    schema = media.get("schema") or {}
    ref = schema.get("$ref")
    if ref is not None:
        schema = resolve_ref(spec, ref)
    return schema


def inner_data_schema(
    spec: dict[str, Any],
    path: str,
    method: str,
    status: str,
) -> dict[str, Any] | None:
    """Return the inner ``data`` schema, following envelope wrappers.

    Returns ``None`` when the wrapper does not expose a typed ``data``
    property (e.g. plain ``ResponseDTO`` without a payload, or the
    un-parameterized ``CollectionDataResponseDTO`` base). Callers
    should treat ``None`` as "spec does not describe this DTO" and
    skip rather than fail.
    """
    wrapper = response_schema(spec, path, method, status)
    data = (wrapper.get("properties") or {}).get("data")
    if data is None:
        return None
    data_ref = data.get("$ref")
    if data_ref is not None:
        return resolve_ref(spec, data_ref)
    if data.get("type") == "array":
        items = data.get("items") or {}
        items_ref = items.get("$ref")
        if items_ref is not None:
            return resolve_ref(spec, items_ref)
        return items if items else None
    return data if data.get("properties") else None


def _sdk_alias(model: type[BaseModel], field_name: str) -> str:
    field = model.model_fields[field_name]
    return field.serialization_alias or field.alias or field_name


def sdk_aliases(model: type[BaseModel]) -> frozenset[str]:
    """Return the over-the-wire names for every field on ``model``."""
    return frozenset(_sdk_alias(model, name) for name in model.model_fields)


def sdk_required_aliases(model: type[BaseModel]) -> frozenset[str]:
    """Return aliases of fields the SDK treats as required."""
    return frozenset(
        _sdk_alias(model, name)
        for name, field in model.model_fields.items()
        if field.is_required()
    )


def spec_required(schema: dict[str, Any]) -> frozenset[str]:
    return frozenset(schema.get("required") or ())


def spec_properties(schema: dict[str, Any]) -> frozenset[str]:
    return frozenset((schema.get("properties") or {}).keys())


def required_diff(model: type[BaseModel], schema: dict[str, Any]) -> Diff:
    sdk = sdk_required_aliases(model)
    spec = spec_required(schema)
    return Diff(
        only_in_sdk=frozenset(sdk - spec),
        only_in_spec=frozenset(spec - sdk),
    )


def property_diff(model: type[BaseModel], schema: dict[str, Any]) -> Diff:
    sdk = sdk_aliases(model)
    spec = spec_properties(schema)
    return Diff(
        only_in_sdk=frozenset(sdk - spec),
        only_in_spec=frozenset(spec - sdk),
    )


def _enum_values(annotation: Any) -> frozenset[str] | None:
    """Extract string enum values from a (possibly ``| None``) annotation."""
    candidates: list[Any] = []
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        candidates.append(annotation)
    else:
        args = getattr(annotation, "__args__", None) or ()
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, Enum):
                candidates.append(arg)
    if not candidates:
        return None
    enum_cls = candidates[0]
    return frozenset(str(member.value) for member in enum_cls)


def _spec_enum_for_field(
    properties: dict[str, Any],
    alias: str,
) -> frozenset[str] | None:
    spec_field = properties.get(alias)
    if not isinstance(spec_field, dict):
        return None
    spec_values = spec_field.get("enum")
    if not isinstance(spec_values, list):
        return None
    return frozenset(str(value) for value in spec_values)


def enum_diffs(
    model: type[BaseModel],
    schema: dict[str, Any],
) -> list[EnumDiff]:
    """Report OpenAPI enum values not covered by the SDK ``Enum``.

    Only ``enum`` is consulted — ``pattern`` is known to be inconsistent
    with ``enum`` in at least one place in the vendor spec (see issue
    #98 notes on FOLDER_TAG) and is ignored here.
    """
    properties = schema.get("properties") or {}
    diffs: list[EnumDiff] = []
    for name, field in model.model_fields.items():
        sdk_values = _enum_values(field.annotation)
        if sdk_values is None:
            continue
        alias = _sdk_alias(model, name)
        spec_values = _spec_enum_for_field(properties, alias)
        if spec_values is None:
            continue
        missing = spec_values - sdk_values
        if missing:
            diffs.append(EnumDiff(field=alias, missing_in_sdk=missing))
    return diffs
