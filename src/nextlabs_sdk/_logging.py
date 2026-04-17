from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from urllib.parse import parse_qsl, urlencode

import httpx

logger = logging.getLogger("nextlabs_sdk")

_DEFAULT_BODY_LIMIT = 2000
_REDACTED = "***"
_REDACTED_HEADER_NAMES = frozenset(("authorization", "proxy-authorization", "cookie"))
_REDACTED_BODY_FIELDS = frozenset(
    (
        "password",
        "client_secret",
        "refresh_token",
        "access_token",
        "id_token",
    ),
)


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for name, header_value in headers.items():
        lower = name.lower()
        if lower in _REDACTED_HEADER_NAMES:
            if lower == "authorization" and header_value.lower().startswith("bearer "):
                redacted[name] = f"Bearer {_REDACTED}"
            else:
                redacted[name] = _REDACTED
        else:
            redacted[name] = header_value
    return redacted


def _redact_json(node: object) -> object:
    if isinstance(node, dict):
        return {
            key: (_REDACTED if key in _REDACTED_BODY_FIELDS else _redact_json(child))
            for key, child in node.items()
        }
    if isinstance(node, list):
        return [_redact_json(element) for element in node]
    return node


def _redact_form(body_text: str) -> str:
    pairs = parse_qsl(body_text, keep_blank_values=True)
    redacted = [
        (key, _REDACTED if key in _REDACTED_BODY_FIELDS else field_value)
        for key, field_value in pairs
    ]
    return urlencode(redacted)


def _decode_utf8(body: bytes) -> str | None:
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _body_preview(content_type: str | None, body: bytes) -> str:
    if not body:
        return "<empty>"
    text = _decode_utf8(body)
    if text is None:
        return f"<binary, {len(body)} bytes>"
    return _dispatch_redaction(content_type, text)


def _dispatch_redaction(content_type: str | None, text: str) -> str:
    ctype = (content_type or "").lower()
    if "application/x-www-form-urlencoded" in ctype:
        return _redact_form(text)
    if "application/json" not in ctype:
        return text
    try:
        parsed = json.loads(text)
    except ValueError:
        return text
    return json.dumps(_redact_json(parsed))


def redact_body(content_type: str | None, body: bytes) -> str:
    return _body_preview(content_type, body)


def truncate(text: str, limit: int = _DEFAULT_BODY_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}… (truncated, {len(text)} bytes total)"


def format_request_line(request: httpx.Request) -> str:
    return f"→ {request.method} {request.url}"


def format_response_line(response: httpx.Response, elapsed_s: float) -> str:
    size = len(response.content)
    reason = response.reason_phrase or ""
    return f"← {response.status_code} {reason} ({size} bytes) in {elapsed_s:.3f}s"
