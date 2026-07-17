from __future__ import annotations

import functools
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TypeVar, cast

from pydantic import BaseModel

from nextlabs_sdk._cloudaz._engine._dialect import CLASSIC_ENVELOPE, PageDialect
from nextlabs_sdk._cloudaz._engine._request_plan import RequestPlan
from nextlabs_sdk._cloudaz._engine._spec import PaginatedSpec
from nextlabs_sdk._cloudaz._search import SearchCriteria

_ModelT = TypeVar("_ModelT", bound=BaseModel)


_QueryArgs = Mapping[str, object]
_ExtraParamsFn = Callable[[_QueryArgs], Mapping[str, str]]


@dataclass(frozen=True)
class _QueryPlanConfig:
    """Fixed inputs to ``_build_query_plan``, bound once via ``partial``."""

    path_template: str
    dialect: PageDialect
    extra_params: _ExtraParamsFn | None


def _build_query_plan(
    config: _QueryPlanConfig,
    args: Mapping[str, object],
    page_no: int,
    page_size: int | None,
) -> RequestPlan:
    path = config.path_template.format(**args)
    query_params: dict[str, int | str] = {config.dialect.page_param: page_no}
    if page_size is not None:
        query_params[config.dialect.size_param] = page_size
    if config.extra_params is not None:
        query_params.update(config.extra_params(args))
    return RequestPlan("GET", path, params=query_params, json=None)


def _build_search_plan(
    path_template: str,
    args: Mapping[str, object],
    page_no: int,
    page_size: int | None,  # noqa: WPS110
) -> RequestPlan:
    path = path_template.format(**args)
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
    extra_params: _ExtraParamsFn | None = None,
) -> PaginatedSpec[_ModelT]:
    """Build a spec for a query-string-paged GET endpoint.

    Args:
        model: The response entry model to validate pages against.
        path_template: A ``str.format`` template interpolated from
            ``plan_builder``'s ``args`` mapping (e.g. ``"/foo/{group}"``).
        dialect: The paging query-parameter vocabulary to use.
        extra_params: Optional callable deriving additional query
            parameters from ``args``, merged alongside the dialect's page
            params (e.g. a per-call flag beyond ``pageNo``/``pageSize``).

    Returns:
        A ``PaginatedSpec`` whose ``plan_builder`` yields a GET
        ``RequestPlan`` with the interpolated path and dialect page params.
    """
    return PaginatedSpec(
        model=model,
        dialect=dialect,
        plan_builder=functools.partial(
            _build_query_plan,
            _QueryPlanConfig(path_template, dialect, extra_params),
        ),
    )


def search_paginated(
    model: type[_ModelT],
    path_template: str,
    *,
    dialect: PageDialect = CLASSIC_ENVELOPE,
) -> PaginatedSpec[_ModelT]:
    """Build a spec for a body-paged search POST endpoint.

    Args:
        model: The response entry model to validate pages against.
        path_template: A ``str.format`` template interpolated from
            ``plan_builder``'s ``args`` mapping (e.g.
            ``"/foo/search/{scope}"``). Endpoints with a fixed path work
            unchanged, since a template without placeholders formats to
            itself.
        dialect: The paging query-parameter vocabulary (unused for paging,
            which lives in the request body via ``criteria.page()``).

    Returns:
        A ``PaginatedSpec`` whose ``plan_builder`` yields a POST
        ``RequestPlan`` with the interpolated path and paged
        ``SearchCriteria`` body.
    """
    return PaginatedSpec(
        model=model,
        dialect=dialect,
        plan_builder=functools.partial(_build_search_plan, path_template),
    )
