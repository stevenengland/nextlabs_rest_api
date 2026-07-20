from __future__ import annotations

import functools
from collections.abc import Mapping
from typing import TypeVar

import httpx
from pydantic import BaseModel

from nextlabs_sdk._cloudaz._engine._assembly import assemble_page
from nextlabs_sdk._cloudaz._engine._spec import PaginatedSpec
from nextlabs_sdk._pagination import PageResult, SyncPaginator

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class SyncEndpointRunner:
    """Interprets a :class:`PaginatedSpec` against a sync ``httpx.Client``."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def pages(
        self,
        spec: PaginatedSpec[_ModelT],
        args: Mapping[str, object],
        *,
        page_size: int | None = None,
    ) -> SyncPaginator[_ModelT]:
        """Build a lazy paginator over the endpoint described by ``spec``.

        Args:
            spec: The endpoint spec describing how to build each page's
                request and parse its response.
            args: Path/body arguments interpolated by ``spec.plan_builder``.
            page_size: Optional page size override forwarded to the plan
                builder.

        Returns:
            A ``SyncPaginator`` that issues no HTTP call until iteration
            begins.
        """
        fetch_page = functools.partial(self._fetch_page, spec, args, page_size)
        return SyncPaginator(fetch_page=fetch_page)

    def _fetch_page(
        self,
        spec: PaginatedSpec[_ModelT],
        args: Mapping[str, object],
        page_size: int | None,
        page_no: int,
    ) -> PageResult[_ModelT]:
        plan = spec.plan_builder(args, page_no, page_size)
        if plan.method == "GET":
            response = self._client.get(plan.path, params=plan.params)
        else:
            response = self._client.post(plan.path, json=plan.json, params=plan.params)
        return assemble_page(response, spec.model, page_no, spec.dialect)
