"""Walk the OpenAPI spec and yield response-body examples as ExampleCase records."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from tests._openapi.spec import load_spec


@dataclass(frozen=True)
class ExampleCase:
    """One vendor-supplied response example.

    Attributes:
        path: OpenAPI path template (unmodified).
        method: Lowercase HTTP method.
        status: HTTP status code as string (matches OpenAPI key format).
        content_type: Response content-type key from the spec.
        body: Raw example string exactly as the vendor wrote it. The
            consumer is responsible for calling ``substitute`` before
            parsing.
    """

    path: str
    method: str
    status: str
    content_type: str
    body: str


def collect_example_cases() -> Iterator[ExampleCase]:
    """Yield one ExampleCase per response-body example found in the spec."""
    spec = load_spec()
    for path, operations in spec.get("paths", {}).items():
        yield from _walk_operations(path, operations)


def _walk_operations(
    path: str,
    operations: Any,
) -> Iterator[ExampleCase]:
    if not isinstance(operations, dict):
        return
    for method, op in operations.items():
        if not isinstance(op, dict):
            continue
        yield from _walk_responses(path, method, op.get("responses", {}))


def _walk_responses(
    path: str,
    method: str,
    responses: dict[str, Any],
) -> Iterator[ExampleCase]:
    for status, resp in responses.items():
        for content_type, media in (resp or {}).get("content", {}).items():
            body = _extract_body(media.get("example"))
            if body is not None:
                yield ExampleCase(
                    path=path,
                    method=method,
                    status=status,
                    content_type=content_type,
                    body=body,
                )


def _extract_body(example: Any) -> str | None:
    """Return the example as a string, serializing dict/list examples to JSON.

    NextLabs' spec mixes conventions: ``*/*`` responses carry hand-written
    string blobs (sometimes with embedded ``{id}`` placeholders that make
    them invalid JSON on their own), while ``application/json`` responses
    carry structured dict examples. We preserve both so downstream layers
    see every documented example.
    """
    if example is None:
        return None
    if isinstance(example, str):
        return example
    if isinstance(example, (dict, list)):
        return json.dumps(example)
    return None
