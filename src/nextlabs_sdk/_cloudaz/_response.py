from __future__ import annotations

from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from nextlabs_sdk._envelope import envelope_from_mapping
from nextlabs_sdk._json_response import decode_json, decode_json_object, require_key
from nextlabs_sdk._pagination import PageResult
from nextlabs_sdk.exceptions import ApiError, NotFoundError, raise_for_status

_ModelT = TypeVar("_ModelT", bound=BaseModel)

# The CloudAz envelope signals "the query matched nothing" with this exact
# statusCode plus a message naming the condition. Both signals are required:
# either alone is treated as a generic error, not a no-data outcome.
_NO_DATA_STATUS_CODE = "5000"
_NO_DATA_MESSAGE_TOKEN = "no data found"


def _request_context(response: httpx.Response) -> tuple[str | None, str | None]:
    try:
        request = response.request
    except RuntimeError:
        return None, None
    return request.method, str(request.url)


def _is_no_data_envelope(raw_code: str | None, message: str | None) -> bool:
    """Return True when the envelope signals the CloudAz no-data outcome.

    The discriminator requires both ``statusCode == "5000"`` and a
    message containing ``"no data found"`` as a case-insensitive
    substring. Either signal alone is a generic error.
    """
    if raw_code != _NO_DATA_STATUS_CODE or message is None:
        return False
    return _NO_DATA_MESSAGE_TOKEN in message.lower()


def _no_data_not_found(
    raw_code: str | None,
    message: str | None,
    response: httpx.Response,
) -> NotFoundError:
    """Build the NotFoundError for a single-fetch no-data envelope.

    The raised error preserves the envelope status code and message.
    """
    request_method, request_url = _request_context(response)
    return NotFoundError(
        message or f"CloudAz no data found (statusCode={raw_code})",
        status_code=response.status_code,
        response_body=response.text,
        request_method=request_method,
        request_url=request_url,
        envelope_status_code=raw_code,
        envelope_message=message,
    )


def _raise_for_envelope_error(
    raw_code: str | None,
    message: str | None,
    response: httpx.Response,
) -> None:
    """Raise ApiError when the CloudAz envelope carries a non-success code.

    The envelope convention is:
        {"statusCode": "<code>", "message": "<text>", "data": <payload>}
    where statusCode values starting with "1" indicate success and any
    other value indicates an error. Returns silently when there is no
    statusCode (legacy non-envelope bodies) or when it indicates success.
    The no-data outcome is handled by callers before reaching this guard.
    """
    if raw_code is None or raw_code.startswith("1"):
        return

    text = message or f"CloudAz error (statusCode={raw_code})"
    request_method, request_url = _request_context(response)

    raise ApiError(
        text,
        status_code=response.status_code,
        response_body=response.text,
        request_method=request_method,
        request_url=request_url,
        envelope_status_code=raw_code,
        envelope_message=message,
    )


def parse_data(response: httpx.Response) -> Any:
    """Extract the 'data' field from a CloudAz API response envelope.

    A no-data envelope on a single-resource fetch raises
    :class:`NotFoundError`, preserving the envelope status code and
    message.
    """
    raise_for_status(response)
    body = decode_json_object(response)
    raw_code, message = envelope_from_mapping(body)
    if _is_no_data_envelope(raw_code, message):
        raise _no_data_not_found(raw_code, message, response)
    _raise_for_envelope_error(raw_code, message, response)
    return require_key(body, "data")


def parse_paginated(response: httpx.Response) -> tuple[Any, int, int, int | None]:
    """Extract data, total_pages, total_records, and page_size from a paginated response.

    The fourth element is the server-reported ``pageSize`` (the effective page
    size the server used). It is ``None`` when the envelope omits the field, in
    which case callers should fall back to the length of the returned page.

    A no-data envelope yields an empty page — ``([], 0, 0, 0)`` — so the
    paginator terminates cleanly without raising.
    """
    raise_for_status(response)
    body = decode_json_object(response)
    raw_code, message = envelope_from_mapping(body)
    if _is_no_data_envelope(raw_code, message):
        return [], 0, 0, 0
    _raise_for_envelope_error(raw_code, message, response)
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

    A no-data envelope yields an empty page — ``([], 0, 0)`` — so the
    paginator terminates cleanly without raising.
    """
    raise_for_status(response)
    body = decode_json_object(response)
    raw_code, message = envelope_from_mapping(body)
    if _is_no_data_envelope(raw_code, message):
        return [], 0, 0
    _raise_for_envelope_error(raw_code, message, response)
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
