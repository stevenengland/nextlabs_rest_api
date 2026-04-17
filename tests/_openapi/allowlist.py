"""Vendor examples that are genuinely malformed and cannot be parsed.

Each entry must carry a comment naming the spec path and the reason. Keep
this list short; a growing list indicates the normalizer or the registry
needs attention rather than a waiver.
"""

from __future__ import annotations

# Format: (path, method, status)
KNOWN_UNPARSEABLE: frozenset[tuple[str, str, str]] = frozenset(
    {
        # Populated during Task 6 after running the round-trip suite and
        # triaging each failure. Empty on purpose.
    },
)
