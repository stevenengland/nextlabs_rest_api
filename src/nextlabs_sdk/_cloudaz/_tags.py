from __future__ import annotations

from collections.abc import Mapping

import httpx

from nextlabs_sdk._cloudaz._engine._async_runner import AsyncEndpointRunner
from nextlabs_sdk._cloudaz._engine._constructors import query_paginated
from nextlabs_sdk._cloudaz._engine._runner import SyncEndpointRunner
from nextlabs_sdk._cloudaz._models import Tag, TagType
from nextlabs_sdk._cloudaz._response import parse_data
from nextlabs_sdk._pagination import AsyncPaginator, SyncPaginator
from nextlabs_sdk.exceptions import raise_for_status

_TAG_TYPE_ARG = "tag_type"
_SHOW_HIDDEN_ARG = "show_hidden"
_SHOW_HIDDEN_PARAM = "showHidden"


def _show_hidden_param(args: Mapping[str, object]) -> dict[str, str]:
    """Derive the optional ``showHidden`` query flag from call args."""
    show_hidden = args.get(_SHOW_HIDDEN_ARG)
    if show_hidden is None:
        return {}
    return {_SHOW_HIDDEN_PARAM: "true" if show_hidden else "false"}


_LIST_SPEC = query_paginated(
    Tag,
    f"/console/api/v1/config/tags/list/{{{_TAG_TYPE_ARG}}}",
    extra_params=_show_hidden_param,
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
