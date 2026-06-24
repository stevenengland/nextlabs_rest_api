"""Delta model types for the policy diff engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Literal


@dataclass(frozen=True)
class FieldChange:
    """A single field-level change between two policy payloads."""

    path: tuple[str, ...]
    kind: Literal["add", "remove", "change"]
    old: object | None
    new: object | None


@dataclass(frozen=True)
class DiffResult:
    """The structured result of comparing two policy payloads."""

    changes: tuple[FieldChange, ...]
    hidden_noise_count: int


@dataclass(frozen=True)
class DiffHeader:
    """Identity of a policy diff: the policy and the two compared revisions."""

    policy_name: str
    policy_id: int
    from_rev: int
    to_rev: int


def _to_jsonable(value: object) -> object:  # noqa: WPS110
    """Convert a change value into a JSON-serialisable structure.

    Identity summaries (``ComponentSummary``, ``ObligationSummary``) reach the
    JSON path as frozen dataclass instances, which ``json.dumps`` cannot encode;
    they are expanded to plain mappings here so component and obligation deltas
    serialise alongside scalar ones.
    """
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, list):
        return [_to_jsonable(element) for element in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(child) for key, child in value.items()}
    return value


def diff_result_to_dict(delta: DiffResult) -> dict[str, object]:
    """Render a :class:`DiffResult` as a JSON-serialisable mapping.

    Each change enumerates its ``path`` (as a list of segments), ``kind``,
    ``old`` value and ``new`` value.
    """
    return {
        "changes": [
            {
                "path": list(change.path),
                "kind": change.kind,
                "old": _to_jsonable(change.old),
                "new": _to_jsonable(change.new),
            }
            for change in delta.changes
        ],
        "hidden_noise_count": delta.hidden_noise_count,
    }
