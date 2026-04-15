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
