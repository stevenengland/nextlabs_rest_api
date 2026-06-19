"""Type-driven identity registry for matching policy structure arrays.

Identity is keyed by *schema type* rather than by field name, so every
field that shares a shape is matched through one code path. The five
policy component slots (``subjectComponents``, ``toSubjectComponents``,
``fromResourceComponents``, ``toResourceComponents``, ``actionComponents``)
all carry ``ComponentDTORes`` elements and are therefore flattened and
matched identically.
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

COMPONENT_SLOT_FIELDS: frozenset[str] = frozenset(
    (
        "subjectComponents",
        "toSubjectComponents",
        "fromResourceComponents",
        "toResourceComponents",
        "actionComponents",
    )
)


@dataclass(frozen=True)
class ComponentSummary:
    """A referenced component reduced to its identity and version."""

    component_id: int | None
    name: str | None
    version: int | None


def _component_dto_key(element: Mapping[str, object]) -> Hashable | None:
    component_id = element.get("id")
    if component_id is not None:
        return ("id", component_id)
    name = element.get("name")
    if name is not None:
        return ("name", name)
    return None


_KEY_RESOLVERS = MappingProxyType(
    {
        "ComponentDTORes": _component_dto_key,
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


def _collect_component(
    component: Mapping[str, object],
    collected: dict[Hashable, ComponentSummary],
) -> None:
    key = identity_key("ComponentDTORes", component)
    if key is not None and key not in collected:
        collected[key] = ComponentSummary(
            component_id=_as_int(component.get("id")),
            name=_as_str(component.get("name")),
            version=_as_int(component.get("version")),
        )
    for sub in _as_mappings(component.get("subComponents")):
        _collect_component(sub, collected)


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
        for component in _as_mappings(group.get("components")):
            _collect_component(component, collected)
    return collected


def _as_mappings(value: object) -> list[Mapping[str, object]]:  # noqa: WPS110
    if not isinstance(value, list):
        return []
    return [element for element in value if isinstance(element, Mapping)]


def _as_int(value: object) -> int | None:  # noqa: WPS110
    return value if isinstance(value, int) else None


def _as_str(value: object) -> str | None:  # noqa: WPS110
    return value if isinstance(value, str) else None
