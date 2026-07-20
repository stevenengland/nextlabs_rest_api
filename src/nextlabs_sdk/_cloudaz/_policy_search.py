from __future__ import annotations

import httpx

from nextlabs_sdk._cloudaz._engine._constructors import (
    CRITERIA_ARG,
    query_paginated,
    search_paginated,
)
from nextlabs_sdk._cloudaz._engine._runner import SyncEndpointRunner
from nextlabs_sdk._cloudaz._engine._async_runner import AsyncEndpointRunner
from nextlabs_sdk._cloudaz._policy_models import PolicyLite
from nextlabs_sdk._cloudaz._response import parse_data
from nextlabs_sdk._cloudaz._search import SavedSearch, SearchCriteria
from nextlabs_sdk._pagination import AsyncPaginator, SyncPaginator
from nextlabs_sdk.exceptions import raise_for_status

_SEARCH_SPEC = search_paginated(PolicyLite, "/console/api/v1/policy/search")
_SEARCH_NAMED_SPEC = search_paginated(
    PolicyLite,
    "/console/api/v1/policy/search/{search}",
)
_SAVED_SEARCHES_SPEC = query_paginated(
    SavedSearch,
    "/console/api/v1/policy/search/savedlist",
)
_FIND_SAVED_SEARCH_SPEC = query_paginated(
    SavedSearch,
    "/console/api/v1/policy/search/savedlist/{name}",
)

_SEARCH_ARG = "search"
_NAME_ARG = "name"


class PolicySearchService:  # noqa: WPS214

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._runner = SyncEndpointRunner(client)

    def search(self, criteria: SearchCriteria) -> SyncPaginator[PolicyLite]:
        return self._runner.pages(_SEARCH_SPEC, {CRITERIA_ARG: criteria})

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
        return self._runner.pages(
            _SEARCH_NAMED_SPEC,
            {_SEARCH_ARG: search, CRITERIA_ARG: criteria},
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
        return self._runner.pages(_SAVED_SEARCHES_SPEC, {})

    def find_saved_search(self, name: str) -> SyncPaginator[SavedSearch]:
        return self._runner.pages(_FIND_SAVED_SEARCH_SPEC, {_NAME_ARG: name})

    def delete_search(self, search_id: int) -> None:
        response = self._client.delete(
            f"/console/api/v1/policy/search/remove/{search_id}",
        )
        raise_for_status(response)


class AsyncPolicySearchService:  # noqa: WPS214

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._runner = AsyncEndpointRunner(client)

    def search(self, criteria: SearchCriteria) -> AsyncPaginator[PolicyLite]:
        return self._runner.pages(_SEARCH_SPEC, {CRITERIA_ARG: criteria})

    def search_named(
        self,
        search: str,
        criteria: SearchCriteria,
    ) -> AsyncPaginator[PolicyLite]:
        """Async variant of :py:meth:`PolicySearchService.search_named`."""
        return self._runner.pages(
            _SEARCH_NAMED_SPEC,
            {_SEARCH_ARG: search, CRITERIA_ARG: criteria},
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
        return self._runner.pages(_SAVED_SEARCHES_SPEC, {})

    def find_saved_search(self, name: str) -> AsyncPaginator[SavedSearch]:
        return self._runner.pages(_FIND_SAVED_SEARCH_SPEC, {_NAME_ARG: name})

    async def delete_search(self, search_id: int) -> None:
        response = await self._client.delete(
            f"/console/api/v1/policy/search/remove/{search_id}",
        )
        raise_for_status(response)
