"""Structural diff engine for policy payloads."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Literal

from nextlabs_sdk._cli._diff._identity import (
    COMPONENT_SLOT_FIELDS,
    OBLIGATION_FIELDS,
    ComponentSummary,
    ObligationSummary,
    flatten_slot,
    pair_obligations,
)
from nextlabs_sdk._cli._diff._models import DiffResult, FieldChange

_KIND_ADD: Literal["add"] = "add"
_KIND_REMOVE: Literal["remove"] = "remove"
_KIND_CHANGE: Literal["change"] = "change"

_NOISE_FIELDS: frozenset[str] = frozenset(
    (
        "deploymentTime",
        "deploymentRequest",
        "createdDate",
        "lastUpdatedDate",
        "modifiedBy",
        "modifiedById",
        "deploymentPending",
    )
)


def canonicalise(payload: Mapping[str, object], *, show_all: bool = False) -> object:
    """Reduce a policy payload to a stable, comparison-ready form.

    Arrays are sorted by their canonical content so element re-ordering is
    erased, and deployment-noise fields are dropped. Dict keys are left for
    the caller to sort at serialisation time. With show_all the noise filter
    and array sort are disabled so every raw difference survives.

    Args:
        payload: The alias-keyed policy payload to canonicalise.
        show_all: When True, keep noise fields and original array order.

    Returns:
        A JSON-serialisable structure with noise stripped and arrays sorted
        (unless show_all is set).
    """
    return _canonicalise_value(payload, show_all=show_all)


def _canonicalise_value(value: object, *, show_all: bool) -> object:  # noqa: WPS110
    if isinstance(value, Mapping):
        return _canonicalise_mapping(value, show_all=show_all)
    if isinstance(value, list):
        return _canonicalise_list(value, show_all=show_all)
    return value


def _canonicalise_mapping(
    mapping: Mapping[str, object], *, show_all: bool
) -> dict[str, object]:
    kept: dict[str, object] = {}
    for key, child in mapping.items():
        if not show_all and key in _NOISE_FIELDS:
            continue
        kept[key] = _canonicalise_value(child, show_all=show_all)
    return kept


def _canonicalise_list(elements: list[object], *, show_all: bool) -> list[object]:
    canonical = [_canonicalise_value(elem, show_all=show_all) for elem in elements]
    if show_all:
        return canonical
    return sorted(canonical, key=_canonical)


def diff_payloads(
    old: Mapping[str, object],
    new: Mapping[str, object],
    *,
    show_all: bool = False,
) -> DiffResult:
    """Compare two alias-keyed policy payload dicts and return a structured delta.

    Args:
        old: The baseline policy payload (alias-keyed JSON dict).
        new: The revised policy payload (alias-keyed JSON dict).
        show_all: When True, disables noise filtering and array-order
            normalisation so every raw difference is reported.

    Returns:
        A DiffResult with all detected changes and a count of suppressed
        noise-field differences.
    """
    changes: list[FieldChange] = []

    _diff_dicts(old, new, path=(), show_all=show_all, changes=changes)

    noise_changes = []
    visible_changes = []
    for change in changes:
        if not show_all and change.path and change.path[-1] in _NOISE_FIELDS:
            noise_changes.append(change)
        else:
            visible_changes.append(change)

    hidden_noise_count = len(noise_changes)
    return DiffResult(
        changes=tuple(visible_changes),
        hidden_noise_count=hidden_noise_count,
    )


def _diff_dicts(
    old: Mapping[str, object],
    new: Mapping[str, object],
    *,
    path: tuple[str, ...],
    show_all: bool,
    changes: list[FieldChange],
) -> None:
    all_keys = old.keys() | new.keys()
    for key in all_keys:
        child_path = path + (key,)
        if not show_all and _diff_special_field(
            key, old, new, path=child_path, changes=changes
        ):
            continue
        if key not in old:
            changes.append(
                FieldChange(path=child_path, kind=_KIND_ADD, old=None, new=new[key])
            )
        elif key not in new:
            changes.append(
                FieldChange(path=child_path, kind=_KIND_REMOVE, old=old[key], new=None)
            )
        else:
            _diff_values(
                old[key], new[key], path=child_path, show_all=show_all, changes=changes
            )


def _diff_special_field(
    key: str,
    old: Mapping[str, object],
    new: Mapping[str, object],
    *,
    path: tuple[str, ...],
    changes: list[FieldChange],
) -> bool:
    """Dispatch identity-aware diffing for component-slot and obligation keys.

    Returns:
        True when *key* was handled by a specialised differ, otherwise False.
    """
    old_value = old.get(key)
    new_value = new.get(key)
    if key in COMPONENT_SLOT_FIELDS:
        _diff_component_slot(old_value, new_value, path=path, changes=changes)
        return True
    if key in OBLIGATION_FIELDS:
        _diff_obligation_field(old_value, new_value, path=path, changes=changes)
        return True
    return False


def _diff_component_slot(
    old_value: object,
    new_value: object,
    *,
    path: tuple[str, ...],
    changes: list[FieldChange],
) -> None:
    old_components = flatten_slot(old_value)
    new_components = flatten_slot(new_value)
    for key in old_components.keys() | new_components.keys():
        change = _classify_component(
            path, old_components.get(key), new_components.get(key)
        )
        if change is not None:
            changes.append(change)


def _classify_component(
    path: tuple[str, ...],
    old_summary: ComponentSummary | None,
    new_summary: ComponentSummary | None,
) -> FieldChange | None:
    if old_summary is not None and new_summary is not None:
        if old_summary == new_summary:
            return None
        return FieldChange(
            path=path, kind=_KIND_CHANGE, old=old_summary, new=new_summary
        )
    if new_summary is not None:
        return FieldChange(path=path, kind=_KIND_ADD, old=None, new=new_summary)
    return FieldChange(path=path, kind=_KIND_REMOVE, old=old_summary, new=None)


def _diff_obligation_field(
    old_value: object,
    new_value: object,
    *,
    path: tuple[str, ...],
    changes: list[FieldChange],
) -> None:
    for old_obl, new_obl in pair_obligations(old_value, new_value):
        label = _obligation_label(new_obl if old_obl is None else old_obl)
        if old_obl is not None and new_obl is not None:
            _diff_dicts(
                old_obl,
                new_obl,
                path=path + (label,),
                show_all=False,
                changes=changes,
            )
        elif new_obl is None:
            changes.append(
                FieldChange(
                    path=path,
                    kind=_KIND_REMOVE,
                    old=ObligationSummary(name=label),
                    new=None,
                )
            )
        else:
            changes.append(
                FieldChange(
                    path=path,
                    kind=_KIND_ADD,
                    old=None,
                    new=ObligationSummary(name=label),
                )
            )


def _obligation_label(obligation: Mapping[str, object] | None) -> str:
    if obligation is None:
        return "?"
    name = obligation.get("name")
    return name if isinstance(name, str) else "?"


def _diff_values(
    old: object,
    new: object,
    *,
    path: tuple[str, ...],
    show_all: bool,
    changes: list[FieldChange],
) -> None:
    if isinstance(old, dict) and isinstance(new, dict):
        _diff_dicts(old, new, path=path, show_all=show_all, changes=changes)
    elif isinstance(old, list) and isinstance(new, list):
        _diff_lists(old, new, path=path, show_all=show_all, changes=changes)
    elif old != new:
        changes.append(FieldChange(path=path, kind=_KIND_CHANGE, old=old, new=new))


def _canonical(elem: object) -> str:
    return json.dumps(elem, sort_keys=True)


def _diff_lists(
    old: list[object],
    new: list[object],
    *,
    path: tuple[str, ...],
    show_all: bool,
    changes: list[FieldChange],
) -> None:
    if show_all:
        if old != new:
            changes.append(FieldChange(path=path, kind=_KIND_CHANGE, old=old, new=new))
        return

    old_set = {_canonical(elem) for elem in old}
    new_set = {_canonical(elem) for elem in new}
    if old_set != new_set:
        changes.append(FieldChange(path=path, kind=_KIND_CHANGE, old=old, new=new))
