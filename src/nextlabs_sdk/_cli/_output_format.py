from __future__ import annotations

from enum import Enum


class OutputFormat(str, Enum):
    """CLI output format for list / detail commands.

    - TABLE:  default compact columns, wraps (never truncates).
    - WIDE:   table plus extra columns per resource.
    - DETAIL: sectioned, kubectl-describe-style per-resource output.
    - JSON:   full JSON dump of the model(s).
    """

    TABLE = "table"
    WIDE = "wide"
    DETAIL = "detail"
    JSON = "json"
