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

import logging
from typing import Mapping

import httpx

logger = logging.getLogger("nextlabs_sdk")


def _log_reason(reason: str) -> None:
    logger.debug("envelope decode failed: %s", reason, extra={"reason": reason})


def envelope_from_mapping(
    body: object,
) -> tuple[str | None, str | None]:
    """Return ``(status_code, message)`` from an already-decoded envelope body.

    Accepts any object. Returns ``(None, None)`` when ``body`` is not a
    mapping, is missing ``statusCode``, or when ``statusCode`` is not a
    string. Returns ``(status_code, None)`` when ``statusCode`` is a
    string but ``message`` is missing, not a string, or an empty string.

    Each ``(None, None)`` return path emits a debug-level log record on
    the ``nextlabs_sdk`` logger with a structured ``reason`` field
    (``body_not_mapping``, ``missing_status_code``, or
    ``status_code_not_string``) to aid diagnosis of surprising server
    responses.

    Never raises.
    """
    if not isinstance(body, Mapping):
        _log_reason("body_not_mapping")
        return None, None

    if "statusCode" not in body:
        _log_reason("missing_status_code")
        return None, None

    raw_code = body.get("statusCode")
    if not isinstance(raw_code, str):
        _log_reason("status_code_not_string")
        return None, None

    raw_message = body.get("message")
    message = raw_message if isinstance(raw_message, str) and raw_message else None
    return raw_code, message


def envelope_from_response(
    response: httpx.Response,
) -> tuple[str | None, str | None]:
    """Return ``(status_code, message)`` from a CloudAz envelope response.

    Both fields are taken verbatim from the response JSON when present
    as strings. Returns ``(None, None)`` when the body is not JSON, not
    a JSON object, is missing ``statusCode``, or when ``statusCode`` is
    not a string. Returns ``(status_code, None)`` when ``statusCode``
    is a string but ``message`` is missing, not a string, or an empty
    string.

    Each ``(None, None)`` return path emits a debug-level log record on
    the ``nextlabs_sdk`` logger with a structured ``reason`` field
    (e.g. ``body_not_json``) — see :func:`envelope_from_mapping` for the
    mapping-level reasons.

    Never raises; safe to call on any ``httpx.Response``.
    """
    try:
        body = response.json()
    except ValueError:
        _log_reason("body_not_json")
        return None, None

    return envelope_from_mapping(body)
