"""Turn ExampleCase records into WireMock stub mappings."""

from __future__ import annotations

import re
from typing import Any

import httpx

from tests._openapi.examples import ExampleCase, collect_example_cases
from tests._openapi.placeholders import substitute

_PATH_PARAM_RE = re.compile(r"\{[^/]+\}")


def build_mapping(case: ExampleCase) -> dict[str, Any]:
    """Build a WireMock mapping dict for a single ExampleCase.

    OpenAPI path parameters (``{id}``) become the regex ``[^/]+``.
    ``*/*`` content is served as ``application/json`` since the SDK
    transport negotiates JSON and vendor examples are JSON-shaped.
    """
    url_pattern = _PATH_PARAM_RE.sub("[^/]+", case.path)
    content_type = (
        "application/json" if case.content_type == "*/*" else case.content_type
    )
    body = substitute(case.body)
    return {
        "request": {
            "method": case.method.upper(),
            "urlPathPattern": url_pattern,
        },
        "response": {
            "status": int(case.status),
            "headers": {"Content-Type": content_type},
            "body": body,
        },
    }


def load_all_mappings(base_url: str) -> None:
    """POST every ExampleCase-derived mapping to the WireMock admin API."""
    admin = f"{base_url}/__admin/mappings"
    with httpx.Client(timeout=10.0) as http:
        http.post(f"{admin}/reset")
        for case in collect_example_cases():
            mapping = build_mapping(case)
            response = http.post(admin, json=mapping)
            response.raise_for_status()
