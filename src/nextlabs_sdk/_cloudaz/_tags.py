from __future__ import annotations

from collections.abc import Mapping

import httpx

from nextlabs_sdk._cloudaz._engine._async_runner import AsyncEndpointRunner
from nextlabs_sdk._cloudaz._engine._dialect import CLASSIC_ENVELOPE
from nextlabs_sdk._cloudaz._engine._request_plan import RequestPlan
from nextlabs_sdk._cloudaz._engine._runner import SyncEndpointRunner
from nextlabs_sdk._cloudaz._engine._spec import PaginatedSpec
from nextlabs_sdk._cloudaz._models import Tag, TagType
from nextlabs_sdk._cloudaz._response import parse_data
from nextlabs_sdk._pagination import AsyncPaginator, SyncPaginator
from nextlabs_sdk.exceptions import raise_for_status

_TAG_TYPE_ARG = "tag_type"
_SHOW_HIDDEN_ARG = "show_hidden"
_SHOW_HIDDEN_PARAM = "showHidden"


def _build_list_plan(
    args: Mapping[str, object],
    page_no: int,
    page_size: int | None,
) -> RequestPlan:
    """Build the ``GET`` plan for listing tags of one type.

    Beyond the classic-envelope page params, this endpoint accepts an
    optional ``showHidden`` query flag, so it cannot use the generic
    ``query_paginated`` constructor unchanged.
    """
    tag_type = args[_TAG_TYPE_ARG]
    query_params: dict[str, int | str] = {CLASSIC_ENVELOPE.page_param: page_no}
    if page_size is not None:
        query_params[CLASSIC_ENVELOPE.size_param] = page_size
    show_hidden = args.get(_SHOW_HIDDEN_ARG)
    if show_hidden is not None:
        query_params[_SHOW_HIDDEN_PARAM] = "true" if show_hidden else "false"
    return RequestPlan(
        "GET",
        f"/console/api/v1/config/tags/list/{tag_type}",
        params=query_params,
        json=None,
    )


_LIST_SPEC = PaginatedSpec(
    model=Tag,
    dialect=CLASSIC_ENVELOPE,
    plan_builder=_build_list_plan,
)


class TagService:

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._runner = SyncEndpointRunner(client)

    def list(
        self,
        tag_type: TagType,
        *,
        page_size: int | None = None,
        show_hidden: bool | None = None,
    ) -> SyncPaginator[Tag]:
        return self._runner.pages(
            _LIST_SPEC,
            {_TAG_TYPE_ARG: tag_type.value, _SHOW_HIDDEN_ARG: show_hidden},
            page_size=page_size,
        )

    def get(self, tag_id: int) -> Tag:
        response = self._client.get(
            f"/console/api/v1/config/tags/{tag_id}",
        )
        return Tag.model_validate(parse_data(response))

    def create(
        self,
        tag_type: TagType,
        *,
        key: str,
        label: str,
    ) -> int:
        payload = {
            "key": key,
            "label": label,
            "type": tag_type.value,
            "status": "ACTIVE",
        }
        response = self._client.post(
            f"/console/api/v1/config/tags/add/{tag_type.value}",
            json=payload,
        )
        return parse_data(response)

    def delete(self, tag_id: int) -> None:
        response = self._client.delete(
            f"/console/api/v1/config/tags/remove/{tag_id}",
        )
        raise_for_status(response)


class AsyncTagService:

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._runner = AsyncEndpointRunner(client)

    def list(
        self,
        tag_type: TagType,
        *,
        page_size: int | None = None,
        show_hidden: bool | None = None,
    ) -> AsyncPaginator[Tag]:
        return self._runner.pages(
            _LIST_SPEC,
            {_TAG_TYPE_ARG: tag_type.value, _SHOW_HIDDEN_ARG: show_hidden},
            page_size=page_size,
        )

    async def get(self, tag_id: int) -> Tag:
        response = await self._client.get(
            f"/console/api/v1/config/tags/{tag_id}",
        )
        return Tag.model_validate(parse_data(response))

    async def create(
        self,
        tag_type: TagType,
        *,
        key: str,
        label: str,
    ) -> int:
        payload = {
            "key": key,
            "label": label,
            "type": tag_type.value,
            "status": "ACTIVE",
        }
        response = await self._client.post(
            f"/console/api/v1/config/tags/add/{tag_type.value}",
            json=payload,
        )
        return parse_data(response)

    async def delete(self, tag_id: int) -> None:
        response = await self._client.delete(
            f"/console/api/v1/config/tags/remove/{tag_id}",
        )
        raise_for_status(response)
