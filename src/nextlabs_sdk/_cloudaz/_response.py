from __future__ import annotations

from typing import Any

import httpx

from nextlabs_sdk._json_response import decode_json, decode_json_object, require_key
from nextlabs_sdk.exceptions import ApiError, raise_for_status


def parse_data(response: httpx.Response) -> Any:
    """Extract the 'data' field from a CloudAz API response envelope."""
    raise_for_status(response)
    body = decode_json_object(response)
    return require_key(body, "data")


def parse_paginated(response: httpx.Response) -> tuple[Any, int, int]:
    """Extract data, total_pages, and total_records from a paginated response."""
    raise_for_status(response)
    body = decode_json_object(response)
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
