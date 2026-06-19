"""Structural diff engine for policy payloads."""

from __future__ import annotations

import json
from collections.abc import Mapping

from nextlabs_sdk._cli._diff._models import DiffResult, FieldChange

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
        if key not in old:
            changes.append(
                FieldChange(path=child_path, kind="add", old=None, new=new[key])
            )
        elif key not in new:
            changes.append(
                FieldChange(path=child_path, kind="remove", old=old[key], new=None)
            )
        else:
            _diff_values(
                old[key], new[key], path=child_path, show_all=show_all, changes=changes
            )


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
        changes.append(FieldChange(path=path, kind="change", old=old, new=new))


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
            changes.append(FieldChange(path=path, kind="change", old=old, new=new))
        return

    old_set = {_canonical(elem) for elem in old}
    new_set = {_canonical(elem) for elem in new}
    if old_set != new_set:
        changes.append(FieldChange(path=path, kind="change", old=old, new=new))
