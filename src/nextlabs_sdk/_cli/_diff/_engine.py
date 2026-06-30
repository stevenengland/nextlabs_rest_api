"""Structural diff engine for policy payloads."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from typing import Literal

from nextlabs_sdk._cli._diff._identity import (
    COMPONENT_SLOT_FIELDS,
    OBLIGATION_FIELDS,
    TAG_FIELDS,
    ObligationSummary,
    flatten_slot,
    pair_obligations,
)
from nextlabs_sdk._cli._diff._identity import TagSummary, pair_tags
from nextlabs_sdk._cli._diff._models import CountMarker, DiffResult, FieldChange
from nextlabs_sdk._cli._diff._slot import compare_slot

_KIND_ADD: Literal["add"] = "add"
_KIND_REMOVE: Literal["remove"] = "remove"
_KIND_CHANGE: Literal["change"] = "change"
_UNKNOWN_LABEL: str = "?"
_OBLIGATION_HEADER_FIELDS: frozenset[str] = frozenset(("id", "name"))

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

_CROSS_POLICY_IDENTITY_FIELDS: frozenset[str] = frozenset(
    (
        "id",
        "name",
        "fullName",
        "folderId",
        "parentId",
        "parentName",
        "version",
        "revisionCount",
        "ownerId",
        "ownerDisplayName",
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
    cross_policy: bool = False,
) -> DiffResult:
    """Compare two alias-keyed policy payload dicts and return a structured delta.

    Args:
        old: The baseline policy payload (alias-keyed JSON dict).
        new: The revised policy payload (alias-keyed JSON dict).
        show_all: When True, disables noise filtering and array-order
            normalisation so every raw difference is reported.
        cross_policy: When True, drop the top-level policy identity fields from
            each side before diffing so they never surface as changes. Nested
            structures are untouched. Ignored when ``show_all`` is set.

    Returns:
        A DiffResult with all detected changes and a count of suppressed
        noise-field differences.
    """
    if cross_policy and not show_all:
        old = _strip_identity_fields(old)
        new = _strip_identity_fields(new)

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
        count_markers=tuple(_collect_count_markers(old, new)),
    )


def _collect_count_markers(
    old: Mapping[str, object], new: Mapping[str, object]
) -> list[CountMarker]:
    """Record old/new element counts for top-level list fields that changed size.

    Obligations, tags and generic arrays count their list elements directly;
    component slots count their flattened members so a component added within an
    existing group is recognised even though the group list itself is unchanged.
    A marker is emitted only when the two counts differ.
    """
    markers: list[CountMarker] = []
    for key in old.keys() | new.keys():
        old_value = old.get(key)
        new_value = new.get(key)
        if not isinstance(old_value, list) and not isinstance(new_value, list):
            continue
        old_count, new_count = _element_counts(key, old_value, new_value)
        if old_count != new_count:
            markers.append(
                CountMarker(path=(key,), old_count=old_count, new_count=new_count)
            )
    return markers


def _element_counts(key: str, old_value: object, new_value: object) -> tuple[int, int]:
    if key in COMPONENT_SLOT_FIELDS:
        return len(flatten_slot(old_value)), len(flatten_slot(new_value))
    old_count = len(old_value) if isinstance(old_value, list) else 0
    new_count = len(new_value) if isinstance(new_value, list) else 0
    return old_count, new_count


def _strip_identity_fields(payload: Mapping[str, object]) -> dict[str, object]:
    """Drop top-level cross-policy identity fields from a payload.

    The strip is shallow on purpose: only the policy's own identity attributes
    are removed, so nested components, obligations and tags keep their own
    identity fields and still diff normally.
    """
    return {
        key: child
        for key, child in payload.items()
        if key not in _CROSS_POLICY_IDENTITY_FIELDS
    }


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
    if key in TAG_FIELDS:
        _diff_tag_field(old_value, new_value, path=path, changes=changes)
        return True
    return False


def _diff_component_slot(
    old_value: object,
    new_value: object,
    *,
    path: tuple[str, ...],
    changes: list[FieldChange],
) -> None:
    for change in compare_slot(old_value, new_value):
        changes.append(replace(change, path=path + change.path))


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
            _expand_obligation(
                old_obl, path=path + (label,), kind=_KIND_REMOVE, changes=changes
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
            _expand_obligation(
                new_obl, path=path + (label,), kind=_KIND_ADD, changes=changes
            )


def _expand_obligation(
    obligation: Mapping[str, object] | None,
    *,
    path: tuple[str, ...],
    kind: Literal["add", "remove"],
    changes: list[FieldChange],
) -> None:
    """Emit a field-line change per leaf of an added/removed obligation payload.

    The obligation's header fields (its ``name`` and the always-null ``id``)
    are skipped because the name is already shown on the summary header; every
    remaining field, including each nested ``params`` entry, is flattened to a
    leaf change so the renderer prints it as a ``+``/``-`` field-line nested
    under that header.
    """
    if obligation is None:
        return
    for key, child in obligation.items():
        if key in _OBLIGATION_HEADER_FIELDS:
            continue
        _expand_obligation_value(child, path=path + (key,), kind=kind, changes=changes)


def _expand_obligation_value(
    value: object,  # noqa: WPS110
    *,
    path: tuple[str, ...],
    kind: Literal["add", "remove"],
    changes: list[FieldChange],
) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            _expand_obligation_value(
                child, path=path + (key,), kind=kind, changes=changes
            )
        return
    old, new = (value, None) if kind == _KIND_REMOVE else (None, value)
    changes.append(FieldChange(path=path, kind=kind, old=old, new=new))


def _obligation_label(obligation: Mapping[str, object] | None) -> str:
    if obligation is None:
        return _UNKNOWN_LABEL
    name = obligation.get("name")
    return name if isinstance(name, str) else _UNKNOWN_LABEL


def _diff_tag_field(
    old_value: object,
    new_value: object,
    *,
    path: tuple[str, ...],
    changes: list[FieldChange],
) -> None:
    for old_tag, new_tag in pair_tags(old_value, new_value):
        display = _tag_display(new_tag if old_tag is None else old_tag)
        if old_tag is not None and new_tag is not None:
            _diff_dicts(
                old_tag,
                new_tag,
                path=path + (display,),
                show_all=False,
                changes=changes,
            )
        elif new_tag is None:
            changes.append(
                FieldChange(
                    path=path,
                    kind=_KIND_REMOVE,
                    old=_tag_summary(old_tag),
                    new=None,
                )
            )
        else:
            changes.append(
                FieldChange(
                    path=path,
                    kind=_KIND_ADD,
                    old=None,
                    new=_tag_summary(new_tag),
                )
            )


def _tag_summary(tag: Mapping[str, object] | None) -> TagSummary:
    if tag is None:
        return TagSummary(key=None, label=None)
    key = tag.get("key")
    label = tag.get("label")
    return TagSummary(
        key=key if isinstance(key, str) else None,
        label=label if isinstance(label, str) else None,
    )


def _tag_display(tag: Mapping[str, object] | None) -> str:
    if tag is None:
        return _UNKNOWN_LABEL
    summary = _tag_summary(tag)
    if summary.key is not None and summary.label is not None:
        return f"{summary.key} ({summary.label.upper()})"
    if summary.key is not None:
        return summary.key
    if summary.label is not None:
        return summary.label
    return _UNKNOWN_LABEL


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

    old_canonical = sorted(_canonical(elem) for elem in old)
    new_canonical = sorted(_canonical(elem) for elem in new)
    if old_canonical != new_canonical:
        changes.append(FieldChange(path=path, kind=_KIND_CHANGE, old=old, new=new))
