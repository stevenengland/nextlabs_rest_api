from __future__ import annotations

from typing import Any

import httpx

from nextlabs_sdk._envelope import envelope_from_response
from nextlabs_sdk._json_response import decode_json, decode_json_object, require_key
from nextlabs_sdk.exceptions import ApiError, raise_for_status


def _request_context(response: httpx.Response) -> tuple[str | None, str | None]:
    try:
        request = response.request
    except RuntimeError:
        return None, None
    return request.method, str(request.url)


def _check_envelope_status(body: dict[str, object], response: httpx.Response) -> None:
    """Raise ApiError if the CloudAz envelope carries a non-success statusCode.

    The envelope convention is:
        {"statusCode": "<code>", "message": "<text>", "data": <payload>}
    where statusCode values starting with "1" indicate success and any
    other value indicates an error (e.g. "5000" = "No data found").
    If the envelope has no statusCode field at all, this returns silently
    to preserve legacy behavior for endpoints that do not use the envelope.
    """
    raw_code, envelope_message = envelope_from_response(response)
    if raw_code is None:
        return
    if raw_code.startswith("1"):
        return

    message = envelope_message or f"CloudAz error (statusCode={raw_code})"
    request_method, request_url = _request_context(response)

    raise ApiError(
        message,
        status_code=response.status_code,
        response_body=response.text,
        request_method=request_method,
        request_url=request_url,
        envelope_status_code=raw_code,
        envelope_message=envelope_message,
    )


def parse_data(response: httpx.Response) -> Any:
    """Extract the 'data' field from a CloudAz API response envelope."""
    raise_for_status(response)
    body = decode_json_object(response)
    _check_envelope_status(body, response)
    return require_key(body, "data")


def parse_paginated(response: httpx.Response) -> tuple[Any, int, int]:
    """Extract data, total_pages, and total_records from a paginated response."""
    raise_for_status(response)
    body = decode_json_object(response)
    _check_envelope_status(body, response)
    total_pages = require_key(body, "totalPages")
    total_records = require_key(body, "totalNoOfRecords")
    if not isinstance(total_pages, int) or not isinstance(total_records, int):
        raise ApiError(
            "Unexpected response shape: pagination fields are not integers",
            status_code=response.status_code,
        )
    return require_key(body, "data"), total_pages, total_records


def parse_reporter_paginated(response: httpx.Response) -> tuple[Any, int, int]:
    """Extract content, total_pages, total_records from a reporter-style response.

    Reporter API nests pagination inside data:
    {"statusCode": ..., "data": {"content": [...], "totalPages": N, "totalElements": N}}
    """
    raise_for_status(response)
    body = decode_json_object(response)
    _check_envelope_status(body, response)
    response_data = require_key(body, "data")
    if not isinstance(response_data, dict):
        raise ApiError(
            "Unexpected response shape: 'data' is not an object",
            status_code=response.status_code,
        )
    content_list = require_key(response_data, "content")
    total_pages = response_data.get("totalPages", 1)
    total_records = response_data.get(
        "totalElements",
        len(content_list) if isinstance(content_list, list) else 0,
    )
    return content_list, total_pages, total_records


def parse_raw(response: httpx.Response) -> Any:
    """Parse a response with no envelope — returns the raw JSON body."""
    raise_for_status(response)
    return decode_json(response)
