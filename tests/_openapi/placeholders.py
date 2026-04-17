"""Substitute vendor example placeholders with deterministic valid values."""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import Mapping

# Runtime inspection of the spec shows {id} is the only placeholder that
# occurs. Add new entries here as future spec refreshes surface them.
_SUBSTITUTIONS: Mapping[str, str] = MappingProxyType({"{id}": "1"})

_PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")


def substitute(body: str) -> str:
    """Replace known vendor placeholders with JSON-valid literals.

    Args:
        body: Raw example string from the OpenAPI spec.

    Returns:
        String where every known placeholder has been replaced.

    Raises:
        ValueError: If the string contains a placeholder not in the
            substitution map. Fail loudly so spec refreshes are reviewed.
    """
    for token, replacement in _SUBSTITUTIONS.items():
        body = body.replace(token, replacement)
    leftover = _PLACEHOLDER_RE.search(body)
    if leftover is not None:
        raise ValueError(
            f"unknown placeholder {leftover.group()!r} — "
            "add it to _SUBSTITUTIONS in tests/_openapi/placeholders.py",
        )
    return body
