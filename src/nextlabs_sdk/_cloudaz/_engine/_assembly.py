from __future__ import annotations

from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from nextlabs_sdk._cloudaz._response import (
    parse_pageable,
    parse_paginated,
    parse_reporter_paginated,
)
from nextlabs_sdk._cloudaz._engine._dialect import PageDialect, PageShape
from nextlabs_sdk._pagination import PageResult
from nextlabs_sdk.exceptions import ApiError

_ModelT = TypeVar("_ModelT", bound=BaseModel)


def assemble_page(
    response: httpx.Response,
    model: type[_ModelT],
    page_no: int,
    dialect: PageDialect,
) -> PageResult[_ModelT]:
    """Parse a paginated CloudAz response into a typed ``PageResult``.

    Dispatches on ``dialect.shape`` to the matching ``_response.py`` parser.
    The classic envelope shape reflects the server-reported ``pageSize``,
    falling back to the length of the returned page when the envelope omits
    it; the reporter and pageable shapes have no server page size, so
    ``page_size`` is always the length of the returned page.
    """
    if dialect.shape is PageShape.CLASSIC_ENVELOPE:
        raw_items, total_pages, total_records, page_size = parse_paginated(response)
    elif dialect.shape is PageShape.REPORTER_ENVELOPE:
        raw_items, total_pages, total_records = parse_reporter_paginated(response)
        page_size = None
    else:
        raw_items, total_pages, total_records = parse_pageable(response)
        page_size = None

    entries = _validate_entries(model, raw_items, response)
    return PageResult(
        entries=entries,
        page_no=page_no,
        page_size=len(entries) if page_size is None else page_size,
        total_pages=total_pages,
        total_records=total_records,
    )


def _validate_entries(
    model: type[_ModelT],
    raw_items: list[object],
    response: httpx.Response,
) -> list[_ModelT]:
    """Validate raw page entries, surfacing schema drift as ``ApiError``.

    ``model.model_validate()`` raises ``pydantic.ValidationError`` on a
    malformed entry; only :class:`NextLabsError` subclasses may escape the
    engine boundary, so it is wrapped here.
    """
    try:
        return [model.model_validate(entry) for entry in raw_items]
    except ValidationError as error:
        raise ApiError(
            f"Unexpected response shape: {error}",
            status_code=response.status_code,
        ) from error
