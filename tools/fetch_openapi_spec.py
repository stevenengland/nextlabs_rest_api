"""Fetch the NextLabs OpenAPI spec and write it to the test fixture path.

Local-only. Refuses to run in CI (where ``CI`` env var is typically set).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

SPEC_URL = "https://developer.nextlabs.com/assets/external/cloudaz/api-docs.json"
TARGET = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "_openapi"
    / "fixtures"
    / "nextlabs-openapi.json"
)


def main() -> int:
    if os.environ.get("CI"):
        sys.stderr.write("fetch_openapi_spec.py refuses to run in CI.\n")
        return 2
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    response = httpx.get(SPEC_URL, timeout=30.0)
    response.raise_for_status()
    TARGET.write_bytes(response.content)
    sys.stdout.write(f"Wrote {len(response.content)} bytes to {TARGET}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
