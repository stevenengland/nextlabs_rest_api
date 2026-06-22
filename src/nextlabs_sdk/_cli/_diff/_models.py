"""Delta model types for the policy diff engine."""

from __future__ import annotations

from dataclasses import dataclass
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
                "old": change.old,
                "new": change.new,
            }
            for change in delta.changes
        ],
        "hidden_noise_count": delta.hidden_noise_count,
    }
