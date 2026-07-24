"""Load the committed vendor OpenAPI spec."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_FIXTURE = Path(__file__).parent / "fixtures" / "nextlabs-openapi.json"


@lru_cache(maxsize=1)
def load_spec() -> dict[str, Any]:
    """Return the parsed OpenAPI document as a plain dict.

    Cached for the process lifetime — the fixture is ~650 KB and parsed
    repeatedly by the round-trip layer and the E2E stub builder.

    Returns:
        The OpenAPI document as a dict.
    """
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))
