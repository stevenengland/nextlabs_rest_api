from __future__ import annotations

import functools

import httpx

from nextlabs_sdk._cloudaz._policy_models import PolicyLite
from nextlabs_sdk._cloudaz._response import parse_data, parse_paginated
from nextlabs_sdk._cloudaz._search import SavedSearch, SearchCriteria
from nextlabs_sdk._pagination import SyncPaginator, PageResult
from nextlabs_sdk.exceptions import raise_for_status

_PAGE_NO_PARAM = "pageNo"


class PolicySearchService:

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def search(self, criteria: SearchCriteria) -> SyncPaginator[PolicyLite]:
        return SyncPaginator(
            fetch_page=functools.partial(self._fetch_search_page, criteria),
        )

    def save_search(self, payload: dict[str, object]) -> int:
        response = self._client.post(
            "/console/api/v1/policy/search/add",
            json=payload,
        )
        return parse_data(response)

    def get_saved_search(self, search_id: int) -> SavedSearch:
        response = self._client.get(
            f"/console/api/v1/policy/search/saved/{search_id}",
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
            f"/console/api/v1/policy/search/remove/{search_id}",
        )
        raise_for_status(response)

    def _fetch_search_page(
        self,
        criteria: SearchCriteria,
        page_no: int,
    ) -> PageResult[PolicyLite]:
        response = self._client.post(
            "/console/api/v1/policy/search",
            json=criteria.page(page_no).to_dict(),
        )
        raw_items, total_pages, total_records = parse_paginated(response)
        entries = [PolicyLite.model_validate(entry) for entry in raw_items]
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
            "/console/api/v1/policy/search/savedlist",
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
            f"/console/api/v1/policy/search/savedlist/{name}",
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
