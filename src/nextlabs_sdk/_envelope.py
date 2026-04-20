"""Tolerant extractor for the CloudAz response envelope.

The CloudAz Console API wraps most responses in a JSON envelope:

    {"statusCode": "<code>", "message": "<text>", "data": <payload>}

Both success and error conditions are signalled by the envelope — codes
with a leading ``1`` indicate success; any other code indicates an
error. The server sometimes returns the same envelope shape even with
non-2xx HTTP statuses (e.g. HTTP 400 with ``{"statusCode": "6000", ...}``
for internal errors), and consumers need the envelope message to
diagnose the problem.

This module exposes a single helper that pulls ``(statusCode, message)``
from a response without raising on malformed input — the helper is
designed for use from both the success parsers in
``_cloudaz/_response.py`` and the HTTP-status error path in
``exceptions.raise_for_status``.
"""

from __future__ import annotations

import httpx


def envelope_from_response(
    response: httpx.Response,
) -> tuple[str | None, str | None]:
    """Return ``(status_code, message)`` from a CloudAz envelope body.

    Both fields are taken verbatim from the response JSON when present
    as strings. Returns ``(None, None)`` when the body is not JSON, not
    a JSON object, is missing ``statusCode``, or when ``statusCode`` is
    not a string. Returns ``(status_code, None)`` when ``statusCode``
    is a string but ``message`` is missing or not a string.

    Never raises; safe to call on any ``httpx.Response``.
    """
    try:
        body = response.json()
    except ValueError:
        return None, None

    if not isinstance(body, dict):
        return None, None

    raw_code = body.get("statusCode")
    if not isinstance(raw_code, str):
        return None, None

    raw_message = body.get("message")
    message = raw_message if isinstance(raw_message, str) and raw_message else None
    return raw_code, message
