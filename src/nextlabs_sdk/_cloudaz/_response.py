from __future__ import annotations

from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from nextlabs_sdk._envelope import envelope_from_mapping
from nextlabs_sdk._json_response import decode_json, decode_json_object, require_key
from nextlabs_sdk._pagination import PageResult
from nextlabs_sdk.exceptions import ApiError, raise_for_status

_ModelT = TypeVar("_ModelT", bound=BaseModel)


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
    raw_code, envelope_message = envelope_from_mapping(body)
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


def parse_paginated(response: httpx.Response) -> tuple[Any, int, int, int | None]:
    """Extract data, total_pages, total_records, and page_size from a paginated response.

    The fourth element is the server-reported ``pageSize`` (the effective page
    size the server used). It is ``None`` when the envelope omits the field, in
    which case callers should fall back to the length of the returned page.
    """
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
    raw_page_size = body.get("pageSize")
    page_size = raw_page_size if isinstance(raw_page_size, int) else None
    return require_key(body, "data"), total_pages, total_records, page_size


def parse_reporter_paginated(response: httpx.Response) -> tuple[Any, int, int]:
    """Extract content, total_pages, total_records from a reporter-style response.

    Used by the ``/v1/`` Reporter endpoints (audit logs, activity logs, policy
    activity reports) which nest pagination inside a CloudAz envelope::

        {"statusCode": ..., "data": {"content": [...], "totalPages": N,
         "totalElements": N}}

    The newer ``/nextlabs-reporter/api/activity-logs/search`` endpoint returns
    a bare Spring ``Page<T>`` without an envelope — use :func:`parse_pageable`
    for that shape instead.
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


def parse_pageable(response: httpx.Response) -> tuple[Any, int, int]:
    """Extract content, total_pages, total_records from a bare Spring Pageable.

    Shape::

        {"content": [...], "totalPages": N, "totalElements": N, ...}

    Unlike :func:`parse_reporter_paginated`, this response has no CloudAz
    envelope and no ``statusCode`` — so the envelope-status check is skipped.
    Used by ``/nextlabs-reporter/api/activity-logs/search``.
    """
    raise_for_status(response)
    body = decode_json_object(response)
    content_list = require_key(body, "content")
    total_pages = require_key(body, "totalPages")
    total_records = require_key(body, "totalElements")
    if not isinstance(total_pages, int) or not isinstance(total_records, int):
        raise ApiError(
            "Unexpected response shape: pagination fields are not integers",
            status_code=response.status_code,
        )
    return content_list, total_pages, total_records


def parse_raw(response: httpx.Response) -> Any:
    """Parse a response with no envelope — returns the raw JSON body."""
    raise_for_status(response)
    return decode_json(response)


def build_page(
    response: httpx.Response,
    model: type[_ModelT],
    page_no: int,
) -> PageResult[_ModelT]:
    """Parse a paginated CloudAz response into a typed ``PageResult``.

    ``PageResult.page_size`` reflects the server-reported ``pageSize``. If the
    envelope omits that field we fall back to the length of the returned page.
    """
    raw_items, total_pages, total_records, page_size = parse_paginated(response)
    entries = [model.model_validate(entry) for entry in raw_items]
    return PageResult(
        entries=entries,
        page_no=page_no,
        page_size=len(entries) if page_size is None else page_size,
        total_pages=total_pages,
        total_records=total_records,
    )
