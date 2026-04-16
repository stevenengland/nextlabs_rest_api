from __future__ import annotations

from typing import Any

import httpx

from nextlabs_sdk.exceptions import raise_for_status


def parse_data(response: httpx.Response) -> Any:
    """Extract the 'data' field from a CloudAz API response envelope."""
    raise_for_status(response)
    body = response.json()
    return body["data"]


def parse_paginated(response: httpx.Response) -> tuple[Any, int, int]:
    """Extract data, total_pages, and total_records from a paginated response."""
    raise_for_status(response)
    body = response.json()
    return body["data"], body["totalPages"], body["totalNoOfRecords"]


def parse_reporter_paginated(response: httpx.Response) -> tuple[Any, int, int]:
    """Extract content, total_pages, total_records from a reporter-style response.

    Reporter API nests pagination inside data:
    {"statusCode": ..., "data": {"content": [...], "totalPages": N, "totalElements": N}}
    """
    raise_for_status(response)
    body = response.json()
    response_data = body["data"]
    content_list = response_data["content"]
    total_pages = response_data.get("totalPages", 1)
    total_records = response_data.get("totalElements", len(content_list))
    return content_list, total_pages, total_records


def parse_raw(response: httpx.Response) -> Any:
    """Parse a response with no envelope — returns the raw JSON body."""
    raise_for_status(response)
    return response.json()
