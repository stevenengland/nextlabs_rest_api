from __future__ import annotations

import functools

import httpx

from nextlabs_sdk._cloudaz._policy_models import PolicyLite
from nextlabs_sdk._cloudaz._response import build_page, parse_data
from nextlabs_sdk._cloudaz._search import SavedSearch, SearchCriteria
from nextlabs_sdk._pagination import AsyncPaginator, PageResult, SyncPaginator
from nextlabs_sdk.exceptions import raise_for_status

_PAGE_NO_PARAM = "pageNo"


class PolicySearchService:

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def search(self, criteria: SearchCriteria) -> SyncPaginator[PolicyLite]:
        return SyncPaginator(
            fetch_page=functools.partial(self._fetch_search_page, criteria),
        )

    def search_named(
        self,
        search: str,
        criteria: SearchCriteria,
    ) -> SyncPaginator[PolicyLite]:
        """Search policies via the path-parameterised ``/policy/search/{search}`` variant.

        The semantics of ``search`` are not documented in the official OpenAPI
        spec; this method forwards the value as a raw path segment. Request
        body and response shape are identical to :py:meth:`search`.
        """
        return SyncPaginator(
            fetch_page=functools.partial(
                self._fetch_search_named_page,
                search,
                criteria,
            ),
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
        return build_page(response, PolicyLite, page_no)

    def _fetch_search_named_page(
        self,
        search: str,
        criteria: SearchCriteria,
        page_no: int,
    ) -> PageResult[PolicyLite]:
        response = self._client.post(
            f"/console/api/v1/policy/search/{search}",
            json=criteria.page(page_no).to_dict(),
        )
        return build_page(response, PolicyLite, page_no)

    def _fetch_saved_searches_page(
        self,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = self._client.get(
            "/console/api/v1/policy/search/savedlist",
            params={_PAGE_NO_PARAM: page_no},
        )
        return build_page(response, SavedSearch, page_no)

    def _fetch_find_saved_search_page(
        self,
        name: str,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = self._client.get(
            f"/console/api/v1/policy/search/savedlist/{name}",
            params={_PAGE_NO_PARAM: page_no},
        )
        return build_page(response, SavedSearch, page_no)


class AsyncPolicySearchService:

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def search(self, criteria: SearchCriteria) -> AsyncPaginator[PolicyLite]:
        return AsyncPaginator(
            fetch_page=functools.partial(self._fetch_search_page, criteria),
        )

    def search_named(
        self,
        search: str,
        criteria: SearchCriteria,
    ) -> AsyncPaginator[PolicyLite]:
        """Async variant of :py:meth:`PolicySearchService.search_named`."""
        return AsyncPaginator(
            fetch_page=functools.partial(
                self._fetch_search_named_page,
                search,
                criteria,
            ),
        )

    async def save_search(self, payload: dict[str, object]) -> int:
        response = await self._client.post(
            "/console/api/v1/policy/search/add",
            json=payload,
        )
        return parse_data(response)

    async def get_saved_search(self, search_id: int) -> SavedSearch:
        response = await self._client.get(
            f"/console/api/v1/policy/search/saved/{search_id}",
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
            f"/console/api/v1/policy/search/remove/{search_id}",
        )
        raise_for_status(response)

    async def _fetch_search_page(
        self,
        criteria: SearchCriteria,
        page_no: int,
    ) -> PageResult[PolicyLite]:
        response = await self._client.post(
            "/console/api/v1/policy/search",
            json=criteria.page(page_no).to_dict(),
        )
        return build_page(response, PolicyLite, page_no)

    async def _fetch_search_named_page(
        self,
        search: str,
        criteria: SearchCriteria,
        page_no: int,
    ) -> PageResult[PolicyLite]:
        response = await self._client.post(
            f"/console/api/v1/policy/search/{search}",
            json=criteria.page(page_no).to_dict(),
        )
        return build_page(response, PolicyLite, page_no)

    async def _fetch_saved_searches_page(
        self,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = await self._client.get(
            "/console/api/v1/policy/search/savedlist",
            params={_PAGE_NO_PARAM: page_no},
        )
        return build_page(response, SavedSearch, page_no)

    async def _fetch_find_saved_search_page(
        self,
        name: str,
        page_no: int,
    ) -> PageResult[SavedSearch]:
        response = await self._client.get(
            f"/console/api/v1/policy/search/savedlist/{name}",
            params={_PAGE_NO_PARAM: page_no},
        )
        return build_page(response, SavedSearch, page_no)
