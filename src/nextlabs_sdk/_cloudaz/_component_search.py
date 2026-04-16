from __future__ import annotations

import functools

import httpx

from nextlabs_sdk._cloudaz._component_models import (
    ComponentLite,
    ComponentNameEntry,
)
from nextlabs_sdk._cloudaz._response import parse_data, parse_paginated
from nextlabs_sdk._cloudaz._search import SavedSearch, SearchCriteria
from nextlabs_sdk._pagination import AsyncPaginator, PageResult, SyncPaginator
from nextlabs_sdk.exceptions import raise_for_status

_PAGE_NO_PARAM = "pageNo"


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

    def list_saved_searches(self) -> SyncPaginator[SavedSearch]:
        return SyncPaginator(
            fetch_page=self._fetch_saved_searches_page,
        )

    def find_saved_search(self, name: str) -> SyncPaginator[SavedSearch]:
        return SyncPaginator(
            fetch_page=functools.partial(
                self._fetch_find_saved_search_page,
                name,
            ),
        )

    def delete_search(self, search_id: int) -> None:
        response = self._client.delete(
            f"/console/api/v1/component/search/remove/{search_id}",
        )
        raise_for_status(response)

    def list_names(self, group: str) -> SyncPaginator[ComponentNameEntry]:
        return SyncPaginator(
            fetch_page=functools.partial(self._fetch_names_page, group),
        )

    def list_names_by_type(
        self,
        group: str,
        component_type: str,
    ) -> SyncPaginator[ComponentNameEntry]:
        return SyncPaginator(
            fetch_page=functools.partial(
                self._fetch_names_by_type_page,
                group,
                component_type,
            ),
        )

    def _fetch_search_page(
        self,
        criteria: SearchCriteria,
        page_no: int,
    ) -> PageResult[ComponentLite]:
        response = self._client.post(
            "/console/api/v1/component/search",
            json=criteria.page(page_no).to_dict(),
        )
        raw_items, total_pages, total_records = parse_paginated(response)
        entries = [ComponentLite.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=total_pages,
            total_records=total_records,
        )

    def _fetch_saved_searches_page(
        self,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = self._client.get(
            "/console/api/v1/component/search/savedlist",
            params={_PAGE_NO_PARAM: page_no},
        )
        raw_items, total_pages, total_records = parse_paginated(response)
        searches = [SavedSearch.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=searches,
            page_no=page_no,
            page_size=len(searches),
            total_pages=total_pages,
            total_records=total_records,
        )

    def _fetch_find_saved_search_page(
        self,
        name: str,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = self._client.get(
            f"/console/api/v1/component/search/savedlist/{name}",
            params={_PAGE_NO_PARAM: page_no},
        )
        raw_items, total_pages, total_records = parse_paginated(response)
        searches = [SavedSearch.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=searches,
            page_no=page_no,
            page_size=len(searches),
            total_pages=total_pages,
            total_records=total_records,
        )

    def _fetch_names_page(
        self,
        group: str,
        page_no: int,
    ) -> PageResult[ComponentNameEntry]:
        response = self._client.get(
            f"/console/api/v1/component/search/listNames/{group}",
            params={_PAGE_NO_PARAM: page_no},
        )
        raw_items, total_pages, total_records = parse_paginated(response)
        entries = [ComponentNameEntry.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=total_pages,
            total_records=total_records,
        )

    def _fetch_names_by_type_page(
        self,
        group: str,
        component_type: str,
        page_no: int,
    ) -> PageResult[ComponentNameEntry]:
        response = self._client.get(
            f"/console/api/v1/component/search/listNames/{group}/{component_type}",
            params={_PAGE_NO_PARAM: page_no},
        )
        raw_items, total_pages, total_records = parse_paginated(response)
        entries = [ComponentNameEntry.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=total_pages,
            total_records=total_records,
        )


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

    def list_saved_searches(self) -> AsyncPaginator[SavedSearch]:
        return AsyncPaginator(
            fetch_page=self._fetch_saved_searches_page,
        )

    def find_saved_search(self, name: str) -> AsyncPaginator[SavedSearch]:
        return AsyncPaginator(
            fetch_page=functools.partial(
                self._fetch_find_saved_search_page,
                name,
            ),
        )

    async def delete_search(self, search_id: int) -> None:
        response = await self._client.delete(
            f"/console/api/v1/component/search/remove/{search_id}",
        )
        raise_for_status(response)

    def list_names(self, group: str) -> AsyncPaginator[ComponentNameEntry]:
        return AsyncPaginator(
            fetch_page=functools.partial(self._fetch_names_page, group),
        )

    def list_names_by_type(
        self,
        group: str,
        component_type: str,
    ) -> AsyncPaginator[ComponentNameEntry]:
        return AsyncPaginator(
            fetch_page=functools.partial(
                self._fetch_names_by_type_page,
                group,
                component_type,
            ),
        )

    async def _fetch_search_page(
        self,
        criteria: SearchCriteria,
        page_no: int,
    ) -> PageResult[ComponentLite]:
        response = await self._client.post(
            "/console/api/v1/component/search",
            json=criteria.page(page_no).to_dict(),
        )
        raw_items, total_pages, total_records = parse_paginated(response)
        entries = [ComponentLite.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=total_pages,
            total_records=total_records,
        )

    async def _fetch_saved_searches_page(
        self,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = await self._client.get(
            "/console/api/v1/component/search/savedlist",
            params={_PAGE_NO_PARAM: page_no},
        )
        raw_items, total_pages, total_records = parse_paginated(response)
        searches = [SavedSearch.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=searches,
            page_no=page_no,
            page_size=len(searches),
            total_pages=total_pages,
            total_records=total_records,
        )

    async def _fetch_find_saved_search_page(
        self,
        name: str,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = await self._client.get(
            f"/console/api/v1/component/search/savedlist/{name}",
            params={_PAGE_NO_PARAM: page_no},
        )
        raw_items, total_pages, total_records = parse_paginated(response)
        searches = [SavedSearch.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=searches,
            page_no=page_no,
            page_size=len(searches),
            total_pages=total_pages,
            total_records=total_records,
        )

    async def _fetch_names_page(
        self,
        group: str,
        page_no: int,
    ) -> PageResult[ComponentNameEntry]:
        response = await self._client.get(
            f"/console/api/v1/component/search/listNames/{group}",
            params={_PAGE_NO_PARAM: page_no},
        )
        raw_items, total_pages, total_records = parse_paginated(response)
        entries = [ComponentNameEntry.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=total_pages,
            total_records=total_records,
        )

    async def _fetch_names_by_type_page(
        self,
        group: str,
        component_type: str,
        page_no: int,
    ) -> PageResult[ComponentNameEntry]:
        response = await self._client.get(
            f"/console/api/v1/component/search/listNames/{group}/{component_type}",
            params={_PAGE_NO_PARAM: page_no},
        )
        raw_items, total_pages, total_records = parse_paginated(response)
        entries = [ComponentNameEntry.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=total_pages,
            total_records=total_records,
        )
