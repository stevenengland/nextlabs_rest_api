from __future__ import annotations

from enum import Enum


class DiffFormat(str, Enum):
    """Human renderer selected by ``policies diff --format``.

    - SEMANTIC: the default sectioned, identity-aware report.
    - UNIFIED:  a canonicalised git-style unified diff.
    """

    SEMANTIC = "semantic"
    UNIFIED = "unified"
