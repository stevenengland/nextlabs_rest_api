"""Parity tests — catches ``required``-set, property, and enum drift on DTOs.

See :mod:`tests._openapi.model_parity` for the pure diff functions and
:mod:`tests._openapi.parity_allowlist` for the opt-outs. New drift must
either be fixed or explicitly added to the allowlist with a reason.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pytest
from pydantic import BaseModel

from tests._openapi import parity_allowlist
from tests._openapi.model_parity import (
    enum_diffs,
    inner_data_schema,
    property_diff,
    required_diff,
)
from tests._openapi.model_registry import iter_entries
from tests._openapi.spec import load_spec


@dataclass(frozen=True)
class _ResolvedEntry:
    path: str
    method: str
    status: str
    model: type[BaseModel]

    @property
    def model_name(self) -> str:
        return self.model.__name__

    @property
    def id(self) -> str:
        return f"{self.model_name}@{self.method.upper()} {self.path}"


def _resolved_entries() -> list[_ResolvedEntry]:
    """Yield one entry per concrete spec path × registered model."""
    spec = load_spec()
    resolved: list[_ResolvedEntry] = []
    for entry in iter_entries():
        for path in spec["paths"]:
            if re.match(entry.pattern, path) is None:
                continue
            resolved.append(
                _ResolvedEntry(
                    path=path,
                    method=entry.method,
                    status=entry.status,
                    model=entry.model,
                ),
            )
    return resolved


_ENTRIES: tuple[_ResolvedEntry, ...] = tuple(_resolved_entries())
_IDS: tuple[str, ...] = tuple(entry.id for entry in _ENTRIES)


def _subtract_allowed(
    extras: frozenset[str],
    model_name: str,
    allowlist: frozenset[tuple[str, str]],
) -> frozenset[str]:
    allowed = {name for (model, name) in allowlist if model == model_name}
    return extras - allowed


def _schema_or_skip(entry: _ResolvedEntry) -> dict[str, object]:
    triple = (entry.path, entry.method, entry.status)
    if triple in parity_allowlist.NO_INNER_SCHEMA:
        pytest.skip(f"spec has no typed inner schema for {entry.id}")
    schema = inner_data_schema(
        load_spec(),
        entry.path,
        entry.method,
        entry.status,
    )
    if schema is None:
        pytest.skip(
            f"spec has no typed inner schema for {entry.id} "
            "(add to parity_allowlist.NO_INNER_SCHEMA)",
        )
    return schema


@pytest.mark.parametrize("entry", _ENTRIES, ids=_IDS)
def test_required_set_parity(entry: _ResolvedEntry) -> None:
    schema = _schema_or_skip(entry)
    diff = required_diff(entry.model, schema)
    only_sdk = _subtract_allowed(
        diff.only_in_sdk,
        entry.model_name,
        parity_allowlist.REQUIRED_ONLY_IN_SDK,
    )
    only_spec = _subtract_allowed(
        diff.only_in_spec,
        entry.model_name,
        parity_allowlist.REQUIRED_ONLY_IN_SPEC,
    )
    assert not only_sdk, (
        f"{entry.id}: SDK requires {sorted(only_sdk)} but spec does not. "
        "Fix the model or add to parity_allowlist.REQUIRED_ONLY_IN_SDK."
    )
    assert not only_spec, (
        f"{entry.id}: spec requires {sorted(only_spec)} but SDK does not. "
        "Fix the model or add to parity_allowlist.REQUIRED_ONLY_IN_SPEC."
    )


@pytest.mark.parametrize("entry", _ENTRIES, ids=_IDS)
def test_property_set_parity(entry: _ResolvedEntry) -> None:
    schema = _schema_or_skip(entry)
    diff = property_diff(entry.model, schema)
    only_sdk = _subtract_allowed(
        diff.only_in_sdk,
        entry.model_name,
        parity_allowlist.PROPERTY_ONLY_IN_SDK,
    )
    only_spec = _subtract_allowed(
        diff.only_in_spec,
        entry.model_name,
        parity_allowlist.PROPERTY_ONLY_IN_SPEC,
    )
    assert not only_sdk, (
        f"{entry.id}: SDK exposes {sorted(only_sdk)} but spec does not. "
        "Fix the model or add to parity_allowlist.PROPERTY_ONLY_IN_SDK."
    )
    assert not only_spec, (
        f"{entry.id}: spec exposes {sorted(only_spec)} but SDK does not. "
        "Fix the model or add to parity_allowlist.PROPERTY_ONLY_IN_SPEC."
    )


@pytest.mark.parametrize("entry", _ENTRIES, ids=_IDS)
def test_enum_value_completeness(entry: _ResolvedEntry) -> None:
    schema = _schema_or_skip(entry)
    allowlist = parity_allowlist.ENUM_ONLY_IN_SPEC
    unexplained: list[str] = []
    for diff in enum_diffs(entry.model, schema):
        missing = {
            value
            for value in diff.missing_in_sdk
            if (entry.model_name, diff.field, value) not in allowlist
        }
        if missing:
            unexplained.append(f"{diff.field}: {sorted(missing)}")
    assert not unexplained, (
        f"{entry.id}: spec enum values missing from SDK Enum: "
        f"{unexplained}. Add the values or list them in "
        "parity_allowlist.ENUM_ONLY_IN_SPEC."
    )
