from __future__ import annotations

import functools

import httpx

from nextlabs_sdk._cloudaz._component_models import (
    ComponentLite,
    ComponentNameEntry,
)
from nextlabs_sdk._cloudaz._response import build_page, parse_data
from nextlabs_sdk._cloudaz._search import SavedSearch, SearchCriteria
from nextlabs_sdk._pagination import AsyncPaginator, PageResult, SyncPaginator
from nextlabs_sdk.exceptions import raise_for_status

_PAGE_NO_PARAM = "pageNo"
_PAGE_SIZE_PARAM = "pageSize"


class ComponentSearchService:

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def search(self, criteria: SearchCriteria) -> SyncPaginator[ComponentLite]:
        return SyncPaginator(
            fetch_page=functools.partial(self._fetch_search_page, criteria),
        )

    def save_search(self, payload: dict[str, object]) -> int:
        response = self._client.post(
            "/console/api/v1/component/search/add",
            json=payload,
        )
        return parse_data(response)

    def get_saved_search(self, search_id: int) -> SavedSearch:
        response = self._client.get(
            f"/console/api/v1/component/search/saved/{search_id}",
        )
        return SavedSearch.model_validate(parse_data(response))

    def list_saved_searches(
        self,
        *,
        page_size: int | None = None,
    ) -> SyncPaginator[SavedSearch]:
        return SyncPaginator(
            fetch_page=functools.partial(
                self._fetch_saved_searches_page,
                page_size,
            ),
        )

    def find_saved_search(
        self,
        name: str,
        *,
        page_size: int | None = None,
    ) -> SyncPaginator[SavedSearch]:
        return SyncPaginator(
            fetch_page=functools.partial(
                self._fetch_find_saved_search_page,
                name,
                page_size,
            ),
        )

    def delete_search(self, search_id: int) -> None:
        response = self._client.delete(
            f"/console/api/v1/component/search/remove/{search_id}",
        )
        raise_for_status(response)

    def list_names(
        self,
        group: str,
        *,
        page_size: int | None = None,
    ) -> SyncPaginator[ComponentNameEntry]:
        return SyncPaginator(
            fetch_page=functools.partial(self._fetch_names_page, group, page_size),
        )

    def list_names_by_type(
        self,
        group: str,
        component_type: str,
        *,
        page_size: int | None = None,
    ) -> SyncPaginator[ComponentNameEntry]:
        return SyncPaginator(
            fetch_page=functools.partial(
                self._fetch_names_by_type_page,
                group,
                component_type,
                page_size,
            ),
        )

    def _page_params(
        self,
        page_no: int,
        page_size: int | None = None,
    ) -> dict[str, int]:
        query_params: dict[str, int] = {_PAGE_NO_PARAM: page_no}
        if page_size is not None:
            query_params[_PAGE_SIZE_PARAM] = page_size
        return query_params

    def _fetch_search_page(
        self,
        criteria: SearchCriteria,
        page_no: int,
    ) -> PageResult[ComponentLite]:
        response = self._client.post(
            "/console/api/v1/component/search",
            json=criteria.page(page_no).to_dict(),
        )
        return build_page(response, ComponentLite, page_no)

    def _fetch_saved_searches_page(
        self,
        page_size: int | None,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = self._client.get(
            "/console/api/v1/component/search/savedlist",
            params=self._page_params(page_no, page_size),
        )
        return build_page(response, SavedSearch, page_no)

    def _fetch_find_saved_search_page(
        self,
        name: str,
        page_size: int | None,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = self._client.get(
            f"/console/api/v1/component/search/savedlist/{name}",
            params=self._page_params(page_no, page_size),
        )
        return build_page(response, SavedSearch, page_no)

    def _fetch_names_page(
        self,
        group: str,
        page_size: int | None,
        page_no: int,
    ) -> PageResult[ComponentNameEntry]:
        response = self._client.get(
            f"/console/api/v1/component/search/listNames/{group}",
            params=self._page_params(page_no, page_size),
        )
        return build_page(response, ComponentNameEntry, page_no)

    def _fetch_names_by_type_page(
        self,
        group: str,
        component_type: str,
        page_size: int | None,
        page_no: int,
    ) -> PageResult[ComponentNameEntry]:
        response = self._client.get(
            f"/console/api/v1/component/search/listNames/{group}/{component_type}",
            params=self._page_params(page_no, page_size),
        )
        return build_page(response, ComponentNameEntry, page_no)


class AsyncComponentSearchService:

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def search(self, criteria: SearchCriteria) -> AsyncPaginator[ComponentLite]:
        return AsyncPaginator(
            fetch_page=functools.partial(self._fetch_search_page, criteria),
        )

    async def save_search(self, payload: dict[str, object]) -> int:
        response = await self._client.post(
            "/console/api/v1/component/search/add",
            json=payload,
        )
        return parse_data(response)

    async def get_saved_search(self, search_id: int) -> SavedSearch:
        response = await self._client.get(
            f"/console/api/v1/component/search/saved/{search_id}",
        )
        return SavedSearch.model_validate(parse_data(response))

    def list_saved_searches(
        self,
        *,
        page_size: int | None = None,
    ) -> AsyncPaginator[SavedSearch]:
        return AsyncPaginator(
            fetch_page=functools.partial(
                self._fetch_saved_searches_page,
                page_size,
            ),
        )

    def find_saved_search(
        self,
        name: str,
        *,
        page_size: int | None = None,
    ) -> AsyncPaginator[SavedSearch]:
        return AsyncPaginator(
            fetch_page=functools.partial(
                self._fetch_find_saved_search_page,
                name,
                page_size,
            ),
        )

    async def delete_search(self, search_id: int) -> None:
        response = await self._client.delete(
            f"/console/api/v1/component/search/remove/{search_id}",
        )
        raise_for_status(response)

    def list_names(
        self,
        group: str,
        *,
        page_size: int | None = None,
    ) -> AsyncPaginator[ComponentNameEntry]:
        return AsyncPaginator(
            fetch_page=functools.partial(self._fetch_names_page, group, page_size),
        )

    def list_names_by_type(
        self,
        group: str,
        component_type: str,
        *,
        page_size: int | None = None,
    ) -> AsyncPaginator[ComponentNameEntry]:
        return AsyncPaginator(
            fetch_page=functools.partial(
                self._fetch_names_by_type_page,
                group,
                component_type,
                page_size,
            ),
        )

    def _page_params(
        self,
        page_no: int,
        page_size: int | None = None,
    ) -> dict[str, int]:
        query_params: dict[str, int] = {_PAGE_NO_PARAM: page_no}
        if page_size is not None:
            query_params[_PAGE_SIZE_PARAM] = page_size
        return query_params

    async def _fetch_search_page(
        self,
        criteria: SearchCriteria,
        page_no: int,
    ) -> PageResult[ComponentLite]:
        response = await self._client.post(
            "/console/api/v1/component/search",
            json=criteria.page(page_no).to_dict(),
        )
        return build_page(response, ComponentLite, page_no)

    async def _fetch_saved_searches_page(
        self,
        page_size: int | None,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = await self._client.get(
            "/console/api/v1/component/search/savedlist",
            params=self._page_params(page_no, page_size),
        )
        return build_page(response, SavedSearch, page_no)

    async def _fetch_find_saved_search_page(
        self,
        name: str,
        page_size: int | None,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = await self._client.get(
            f"/console/api/v1/component/search/savedlist/{name}",
            params=self._page_params(page_no, page_size),
        )
        return build_page(response, SavedSearch, page_no)

    async def _fetch_names_page(
        self,
        group: str,
        page_size: int | None,
        page_no: int,
    ) -> PageResult[ComponentNameEntry]:
        response = await self._client.get(
            f"/console/api/v1/component/search/listNames/{group}",
            params=self._page_params(page_no, page_size),
        )
        return build_page(response, ComponentNameEntry, page_no)

    async def _fetch_names_by_type_page(
        self,
        group: str,
        component_type: str,
        page_size: int | None,
        page_no: int,
    ) -> PageResult[ComponentNameEntry]:
        response = await self._client.get(
            f"/console/api/v1/component/search/listNames/{group}/{component_type}",
            params=self._page_params(page_no, page_size),
        )
        return build_page(response, ComponentNameEntry, page_no)
