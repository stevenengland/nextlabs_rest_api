from __future__ import annotations

import functools
import httpx

from nextlabs_sdk._cloudaz._models import Tag, TagType
from nextlabs_sdk._cloudaz._response import parse_data, parse_paginated
from nextlabs_sdk._pagination import AsyncPaginator, PageResult, SyncPaginator
from nextlabs_sdk.exceptions import raise_for_status


def _list_params(
    page_no: int,
    page_size: int | None,
    show_hidden: bool | None,
) -> dict[str, int | str]:
    query_params: dict[str, int | str] = {"pageNo": page_no}
    if page_size is not None:
        query_params["pageSize"] = page_size
    if show_hidden is not None:
        query_params["showHidden"] = "true" if show_hidden else "false"
    return query_params


class TagService:

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def list(
        self,
        tag_type: TagType,
        *,
        page_size: int | None = None,
        show_hidden: bool | None = None,
    ) -> SyncPaginator[Tag]:
        return SyncPaginator(
            fetch_page=functools.partial(
                self._fetch_page,
                tag_type,
                page_size,
                show_hidden,
            ),
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

    def _fetch_page(
        self,
        tag_type: TagType,
        page_size: int | None,
        show_hidden: bool | None,
        page_no: int,
    ) -> PageResult[Tag]:
        response = self._client.get(
            f"/console/api/v1/config/tags/list/{tag_type.value}",
            params=_list_params(page_no, page_size, show_hidden),
        )
        raw_items, total_pages, total_records, server_page_size = parse_paginated(
            response,
        )
        tags = [Tag.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=tags,
            page_no=page_no,
            page_size=len(tags) if server_page_size is None else server_page_size,
            total_pages=total_pages,
            total_records=total_records,
        )


class AsyncTagService:

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def list(
        self,
        tag_type: TagType,
        *,
        page_size: int | None = None,
        show_hidden: bool | None = None,
    ) -> AsyncPaginator[Tag]:
        return AsyncPaginator(
            fetch_page=functools.partial(
                self._fetch_page,
                tag_type,
                page_size,
                show_hidden,
            ),
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

    async def _fetch_page(
        self,
        tag_type: TagType,
        page_size: int | None,
        show_hidden: bool | None,
        page_no: int,
    ) -> PageResult[Tag]:
        response = await self._client.get(
            f"/console/api/v1/config/tags/list/{tag_type.value}",
            params=_list_params(page_no, page_size, show_hidden),
        )
        raw_items, total_pages, total_records, server_page_size = parse_paginated(
            response,
        )
        tags = [Tag.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=tags,
            page_no=page_no,
            page_size=len(tags) if server_page_size is None else server_page_size,
            total_pages=total_pages,
            total_records=total_records,
        )
