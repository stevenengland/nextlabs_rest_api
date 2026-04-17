from __future__ import annotations

import httpx

from nextlabs_sdk.exceptions import ApiError, NextLabsError

_BODY_PREVIEW_LIMIT = 500


def _truncate(text: str | None) -> str | None:
    if text is None:
        return None
    if len(text) <= _BODY_PREVIEW_LIMIT:
        return text
    return f"{text[:_BODY_PREVIEW_LIMIT]}… (truncated)"


def _request_context(response: httpx.Response) -> tuple[str | None, str | None]:
    try:
        request = response.request
    except RuntimeError:
        return None, None
    return request.method, str(request.url)


def decode_json(
    response: httpx.Response,
    *,
    error_cls: type[NextLabsError] = ApiError,
) -> object:
    """Decode a response body as JSON, translating errors into NextLabsError."""
    try:
        return response.json()
    except ValueError as exc:
        method, url = _request_context(response)
        raise error_cls(
            _build_invalid_json_message(response, exc),
            status_code=response.status_code,
            response_body=_truncate(response.text),
            request_method=method,
            request_url=url,
        ) from exc


def _build_invalid_json_message(response: httpx.Response, exc: ValueError) -> str:
    content_type = response.headers.get("content-type") or "unknown"
    redirect_clause = _format_redirect_clause(response)
    return (
        f"Invalid JSON response "
        f"(HTTP {response.status_code}, Content-Type={content_type})"
        f"{redirect_clause}: {exc}"
    )


def _format_redirect_clause(response: httpx.Response) -> str:
    history = response.history
    if not history:
        return ""
    hops = len(history)
    noun = "redirect" if hops == 1 else "redirects"
    original_url = str(history[0].request.url)
    final_url = str(response.request.url)
    return f" after {hops} {noun} from {original_url} to {final_url}"


def decode_json_object(
    response: httpx.Response,
    *,
    error_cls: type[NextLabsError] = ApiError,
    context: str = "",
) -> dict[str, object]:
    """Decode a JSON response and assert it is a mapping."""
    body = decode_json(response, error_cls=error_cls)
    if not isinstance(body, dict):
        raise error_cls(
            f"Unexpected response shape: expected object{context}",
            status_code=response.status_code,
        )
    return body


def require_key(
    body: dict[str, object],
    key: str,
    *,
    error_cls: type[NextLabsError] = ApiError,
    context: str = "",
) -> object:
    """Fetch a required key from a JSON body, translating errors."""
    if key not in body:
        raise error_cls(
            f"Unexpected response shape: missing '{key}'{context}",
        )
    return body[key]


def require_str(
    body: dict[str, object],
    key: str,
    *,
    error_cls: type[NextLabsError] = ApiError,
    context: str = "",
) -> str:
    """Fetch a required string key from a JSON body."""
    raw = require_key(body, key, error_cls=error_cls, context=context)
    if not isinstance(raw, str):
        raise error_cls(
            f"Unexpected response shape: '{key}' is not a string{context}",
        )
    return raw


def require_int(
    body: dict[str, object],
    key: str,
    *,
    error_cls: type[NextLabsError] = ApiError,
    context: str = "",
) -> int:
    """Fetch a required int key from a JSON body (accepts numeric strings)."""
    raw = require_key(body, key, error_cls=error_cls, context=context)
    if isinstance(raw, bool) or not isinstance(raw, (int, str)):
        raise error_cls(
            f"Unexpected response shape: '{key}' is not an integer{context}",
        )
    try:
        return int(raw)
    except ValueError as exc:
        raise error_cls(
            f"Unexpected response shape: '{key}' is not an integer{context}",
        ) from exc
