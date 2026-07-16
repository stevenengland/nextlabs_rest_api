from __future__ import annotations

import functools
from collections.abc import Mapping
from typing import TypeVar, cast

from pydantic import BaseModel

from nextlabs_sdk._cloudaz._engine._dialect import CLASSIC_ENVELOPE, PageDialect
from nextlabs_sdk._cloudaz._engine._request_plan import RequestPlan
from nextlabs_sdk._cloudaz._engine._spec import PaginatedSpec
from nextlabs_sdk._cloudaz._search import SearchCriteria

_ModelT = TypeVar("_ModelT", bound=BaseModel)


def _build_query_plan(
    path_template: str,
    dialect: PageDialect,
    args: Mapping[str, object],
    page_no: int,
    page_size: int | None,
) -> RequestPlan:
    path = path_template.format(**args)
    query_params = {dialect.page_param: page_no}
    if page_size is not None:
        query_params[dialect.size_param] = page_size
    return RequestPlan("GET", path, params=query_params, json=None)


def _build_search_plan(
    path: str,
    args: Mapping[str, object],
    page_no: int,
    page_size: int | None,  # noqa: WPS110
) -> RequestPlan:
    criteria = cast(SearchCriteria, args["criteria"])
    return RequestPlan(
        "POST",
        path,
        params=None,
        json=criteria.page(page_no).to_dict(),
    )


def query_paginated(
    model: type[_ModelT],
    path_template: str,
    *,
    dialect: PageDialect = CLASSIC_ENVELOPE,
) -> PaginatedSpec[_ModelT]:
    """Build a spec for a query-string-paged GET endpoint.

    Args:
        model: The response entry model to validate pages against.
        path_template: A ``str.format`` template interpolated from
            ``plan_builder``'s ``args`` mapping (e.g. ``"/foo/{group}"``).
        dialect: The paging query-parameter vocabulary to use.

    Returns:
        A ``PaginatedSpec`` whose ``plan_builder`` yields a GET
        ``RequestPlan`` with the interpolated path and dialect page params.
    """
    return PaginatedSpec(
        model=model,
        method="GET",
        dialect=dialect,
        plan_builder=functools.partial(_build_query_plan, path_template, dialect),
    )


def search_paginated(
    model: type[_ModelT],
    path: str,
    *,
    dialect: PageDialect = CLASSIC_ENVELOPE,
) -> PaginatedSpec[_ModelT]:
    """Build a spec for a body-paged search POST endpoint.

    Args:
        model: The response entry model to validate pages against.
        path: The fixed request path.
        dialect: The paging query-parameter vocabulary (unused for paging,
            which lives in the request body via ``criteria.page()``).

    Returns:
        A ``PaginatedSpec`` whose ``plan_builder`` yields a POST
        ``RequestPlan`` with the paged ``SearchCriteria`` body.
    """
    return PaginatedSpec(
        model=model,
        method="POST",
        dialect=dialect,
        plan_builder=functools.partial(_build_search_plan, path),
    )
