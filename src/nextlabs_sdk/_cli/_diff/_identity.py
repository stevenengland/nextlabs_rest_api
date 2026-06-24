"""Type-driven identity registry for matching policy structure arrays.

Identity is keyed by *schema type* rather than by field name, so every
field that shares a shape is matched through one code path. The five
policy component slots (``subjectComponents``, ``toSubjectComponents``,
``fromResourceComponents``, ``toResourceComponents``, ``actionComponents``)
all carry ``ComponentDTORes`` elements and are therefore flattened and
matched identically.
"""

from __future__ import annotations

from collections.abc import Hashable, Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeAlias

_Element: TypeAlias = Mapping[str, object]
_ObligationPair: TypeAlias = "tuple[_Element | None, _Element | None]"
_ObligationGroups: TypeAlias = "dict[Hashable, list[_Element]]"

_NAME_FIELD = "name"
_TAG_SCHEMA_TYPE = "Tag"

COMPONENT_SLOT_FIELDS: frozenset[str] = frozenset(
    (
        "subjectComponents",
        "toSubjectComponents",
        "fromResourceComponents",
        "toResourceComponents",
        "actionComponents",
    )
)

OBLIGATION_FIELDS: frozenset[str] = frozenset(("allowObligations", "denyObligations"))

TAG_FIELDS: frozenset[str] = frozenset(("tags",))


@dataclass(frozen=True)
class ObligationSummary:
    """An obligation reduced to the name used to identify it for display."""

    name: str | None


@dataclass(frozen=True)
class ComponentSummary:
    """A referenced component reduced to its identity and version."""

    component_id: int | None
    name: str | None
    version: int | None


@dataclass(frozen=True)
class TagSummary:
    """A tag reduced to its identity fields for display."""

    key: str | None
    label: str | None


def _component_dto_key(element: Mapping[str, object]) -> Hashable | None:
    component_id = element.get("id")
    if component_id is not None:
        return ("id", component_id)
    name = element.get(_NAME_FIELD)
    if name is not None:
        return (_NAME_FIELD, name)
    return None


def _tag_key(element: Mapping[str, object]) -> Hashable | None:
    key = element.get("key")
    if key is not None:
        return ("key", key)
    label = element.get("label")
    if label is not None:
        return ("label", label)
    return None


_KEY_RESOLVERS = MappingProxyType(
    {
        "ComponentDTORes": _component_dto_key,
        _TAG_SCHEMA_TYPE: _tag_key,
    }
)


def identity_key(schema_type: str, element: Mapping[str, object]) -> Hashable | None:
    """Resolve the stable identity key of *element* for *schema_type*.

    Args:
        schema_type: The schema type whose identity rule should be applied.
        element: The alias-keyed element dict to key.

    Returns:
        A hashable identity key, or None when no key can be derived or the
        schema type has no registered resolver.
    """
    resolver = _KEY_RESOLVERS.get(schema_type)
    if resolver is None:
        return None
    return resolver(element)


def walk_group_components(
    group: Mapping[str, object],
) -> Iterator[Mapping[str, object]]:
    """Yield every component in a group, descending into nested subComponents.

    This is the single traversal of the component-group shape (``components``
    holding ``ComponentDTORes`` elements, each reachable sub-tree under
    ``subComponents``). Callers that key components by identity or summarise
    them share this walk so schema-shape changes touch one place.

    Args:
        group: An alias-keyed component group (a mapping with ``components``).

    Yields:
        Each component mapping in the group, including nested subcomponents.
    """
    for component in _as_mappings(group.get("components")):
        yield from _walk_component(component)


def _walk_component(
    component: Mapping[str, object],
) -> Iterator[Mapping[str, object]]:
    yield component
    for sub in _as_mappings(component.get("subComponents")):
        yield from _walk_component(sub)


def flatten_slot(slot_value: object) -> dict[Hashable, ComponentSummary]:
    """Flatten a component slot to the set of referenced components by identity.

    Each slot holds component groups; every group's components, and every
    component reachable through nested ``subComponents``, is collected and
    keyed by its stable identity (id, falling back to name).

    Args:
        slot_value: The alias-keyed slot value (a list of component groups).

    Returns:
        A mapping from identity key to the referenced component's summary.
    """
    collected: dict[Hashable, ComponentSummary] = {}
    for group in _as_mappings(slot_value):
        for component in walk_group_components(group):
            key = identity_key("ComponentDTORes", component)
            if key is not None and key not in collected:
                collected[key] = ComponentSummary(
                    component_id=_as_int(component.get("id")),
                    name=_as_str(component.get("name")),
                    version=_as_int(component.get("version")),
                )
    return collected


def _obligation_group_key(element: Mapping[str, object]) -> Hashable:
    return (element.get(_NAME_FIELD), element.get("policyModelId"))


def pair_obligations(old_value: object, new_value: object) -> list[_ObligationPair]:
    """Pair old and new obligations for comparison.

    Obligations carry a null ``id`` and a non-unique ``name``, so they are
    grouped by ``(name, policyModelId)`` and, within each colliding group,
    paired positionally. Surplus obligations on either side are paired
    against ``None`` so they surface as additions or removals.

    Args:
        old_value: The alias-keyed baseline obligation list.
        new_value: The alias-keyed revised obligation list.

    Returns:
        A list of ``(old, new)`` pairs; either side is ``None`` when the
        colliding group has no positional counterpart.
    """
    old_groups = _group_obligations(old_value)
    new_groups = _group_obligations(new_value)
    pairs: list[_ObligationPair] = []
    for key in _ordered_keys(old_groups, new_groups):
        olds = old_groups.get(key, [])
        news = new_groups.get(key, [])
        for index in range(max(len(olds), len(news))):
            old_obl = olds[index] if index < len(olds) else None
            new_obl = news[index] if index < len(news) else None
            pairs.append((old_obl, new_obl))
    return pairs


def pair_tags(old_value: object, new_value: object) -> list[_ObligationPair]:
    """Pair old and new tags for comparison by identity key.

    Tags are matched by ``key``, falling back to ``label``. Elements with no
    resolvable identity key are silently skipped.

    Args:
        old_value: The alias-keyed baseline tag list.
        new_value: The alias-keyed revised tag list.

    Returns:
        A list of ``(old, new)`` pairs; either side is ``None`` when there is
        no counterpart in that version.
    """
    old_idx = {
        identity_key(_TAG_SCHEMA_TYPE, el): el
        for el in _as_mappings(old_value)
        if identity_key(_TAG_SCHEMA_TYPE, el) is not None
    }
    new_idx = {
        identity_key(_TAG_SCHEMA_TYPE, el): el
        for el in _as_mappings(new_value)
        if identity_key(_TAG_SCHEMA_TYPE, el) is not None
    }
    pairs: list[_ObligationPair] = []
    for tag_key in _ordered_keys(old_idx, new_idx):
        pairs.append((old_idx.get(tag_key), new_idx.get(tag_key)))
    return pairs


def _group_obligations(value: object) -> _ObligationGroups:  # noqa: WPS110
    grouped: _ObligationGroups = {}
    for element in _as_mappings(value):
        grouped.setdefault(_obligation_group_key(element), []).append(element)
    return grouped


def _ordered_keys(
    old_groups: Mapping[Hashable, object], new_groups: Mapping[Hashable, object]
) -> list[Hashable]:
    ordered = list(old_groups)
    for key in new_groups:
        if key not in old_groups:
            ordered.append(key)
    return ordered


def _as_mappings(value: object) -> list[Mapping[str, object]]:  # noqa: WPS110
    if not isinstance(value, list):
        return []
    return [element for element in value if isinstance(element, Mapping)]


def _as_int(value: object) -> int | None:  # noqa: WPS110
    return value if isinstance(value, int) else None


def _as_str(value: object) -> str | None:  # noqa: WPS110
    return value if isinstance(value, str) else None
