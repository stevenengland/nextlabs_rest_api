from __future__ import annotations

import functools

import httpx

from nextlabs_sdk._cloudaz._component_type_models import ComponentType
from nextlabs_sdk._cloudaz._response import parse_data, parse_paginated
from nextlabs_sdk._cloudaz._search import SavedSearch, SearchCriteria
from nextlabs_sdk._pagination import AsyncPaginator, PageResult, SyncPaginator
from nextlabs_sdk.exceptions import raise_for_status

_PAGE_NO_PARAM = "pageNo"
_PAGE_SIZE_PARAM = "pageSize"


def _saved_list_params(page_no: int, page_size: int | None) -> dict[str, int]:
    query_params: dict[str, int] = {_PAGE_NO_PARAM: page_no}
    if page_size is not None:
        query_params[_PAGE_SIZE_PARAM] = page_size
    return query_params


def _saved_search_page_result(
    response: httpx.Response,
    page_no: int,
) -> PageResult[SavedSearch]:
    raw_items, total_pages, total_records, server_page_size = parse_paginated(response)
    searches = [SavedSearch.model_validate(entry) for entry in raw_items]
    return PageResult(
        entries=searches,
        page_no=page_no,
        page_size=len(searches) if server_page_size is None else server_page_size,
        total_pages=total_pages,
        total_records=total_records,
    )


def _component_type_page_result(
    response: httpx.Response,
    page_no: int,
) -> PageResult[ComponentType]:
    raw_items, total_pages, total_records, server_page_size = parse_paginated(response)
    entries = [ComponentType.model_validate(entry) for entry in raw_items]
    return PageResult(
        entries=entries,
        page_no=page_no,
        page_size=len(entries) if server_page_size is None else server_page_size,
        total_pages=total_pages,
        total_records=total_records,
    )


class ComponentTypeSearchService:

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def search(self, criteria: SearchCriteria) -> SyncPaginator[ComponentType]:
        return SyncPaginator(
            fetch_page=functools.partial(self._fetch_search_page, criteria),
        )

    def save_search(self, payload: dict[str, object]) -> int:
        response = self._client.post(
            "/console/api/v1/policyModel/search/add",
            json=payload,
        )
        return parse_data(response)

    def delete_search(self, search_id: int) -> None:
        response = self._client.delete(
            f"/console/api/v1/policyModel/search/remove/{search_id}",
        )
        raise_for_status(response)

    def get_saved_search(self, search_id: int) -> SavedSearch:
        response = self._client.get(
            f"/console/api/v1/policyModel/search/saved/{search_id}",
        )
        return SavedSearch.model_validate(parse_data(response))

    def list_saved_searches(
        self,
        search_type: str,
        *,
        page_size: int | None = None,
    ) -> SyncPaginator[SavedSearch]:
        return SyncPaginator(
            fetch_page=functools.partial(
                self._fetch_saved_searches_page,
                search_type,
                page_size,
            ),
        )

    def find_saved_search(
        self,
        search_type: str,
        name: str,
        *,
        page_size: int | None = None,
    ) -> SyncPaginator[SavedSearch]:
        return SyncPaginator(
            fetch_page=functools.partial(
                self._fetch_find_saved_search_page,
                search_type,
                name,
                page_size,
            ),
        )

    def _fetch_search_page(
        self,
        criteria: SearchCriteria,
        page_no: int,
    ) -> PageResult[ComponentType]:
        response = self._client.post(
            "/console/api/v1/policyModel/search",
            json=criteria.page(page_no).to_dict(),
        )
        return _component_type_page_result(response, page_no)

    def _fetch_saved_searches_page(
        self,
        search_type: str,
        page_size: int | None,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = self._client.get(
            f"/console/api/v1/policyModel/search/savedlist/{search_type}",
            params=_saved_list_params(page_no, page_size),
        )
        return _saved_search_page_result(response, page_no)

    def _fetch_find_saved_search_page(
        self,
        search_type: str,
        name: str,
        page_size: int | None,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = self._client.get(
            f"/console/api/v1/policyModel/search/savedlist/{search_type}/{name}",
            params=_saved_list_params(page_no, page_size),
        )
        return _saved_search_page_result(response, page_no)


class AsyncComponentTypeSearchService:

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def search(self, criteria: SearchCriteria) -> AsyncPaginator[ComponentType]:
        return AsyncPaginator(
            fetch_page=functools.partial(self._fetch_search_page, criteria),
        )

    async def save_search(self, payload: dict[str, object]) -> int:
        response = await self._client.post(
            "/console/api/v1/policyModel/search/add",
            json=payload,
        )
        return parse_data(response)

    async def delete_search(self, search_id: int) -> None:
        response = await self._client.delete(
            f"/console/api/v1/policyModel/search/remove/{search_id}",
        )
        raise_for_status(response)

    async def get_saved_search(self, search_id: int) -> SavedSearch:
        response = await self._client.get(
            f"/console/api/v1/policyModel/search/saved/{search_id}",
        )
        return SavedSearch.model_validate(parse_data(response))

    def list_saved_searches(
        self,
        search_type: str,
        *,
        page_size: int | None = None,
    ) -> AsyncPaginator[SavedSearch]:
        return AsyncPaginator(
            fetch_page=functools.partial(
                self._fetch_saved_searches_page,
                search_type,
                page_size,
            ),
        )

    def find_saved_search(
        self,
        search_type: str,
        name: str,
        *,
        page_size: int | None = None,
    ) -> AsyncPaginator[SavedSearch]:
        return AsyncPaginator(
            fetch_page=functools.partial(
                self._fetch_find_saved_search_page,
                search_type,
                name,
                page_size,
            ),
        )

    async def _fetch_search_page(
        self,
        criteria: SearchCriteria,
        page_no: int,
    ) -> PageResult[ComponentType]:
        response = await self._client.post(
            "/console/api/v1/policyModel/search",
            json=criteria.page(page_no).to_dict(),
        )
        return _component_type_page_result(response, page_no)

    async def _fetch_saved_searches_page(
        self,
        search_type: str,
        page_size: int | None,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = await self._client.get(
            f"/console/api/v1/policyModel/search/savedlist/{search_type}",
            params=_saved_list_params(page_no, page_size),
        )
        return _saved_search_page_result(response, page_no)

    async def _fetch_find_saved_search_page(
        self,
        search_type: str,
        name: str,
        page_size: int | None,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = await self._client.get(
            f"/console/api/v1/policyModel/search/savedlist/{search_type}/{name}",
            params=_saved_list_params(page_no, page_size),
        )
        return _saved_search_page_result(response, page_no)
