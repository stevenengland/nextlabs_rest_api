from __future__ import annotations

import httpx

from nextlabs_sdk._cloudaz._component_type_models import ComponentType
from nextlabs_sdk._cloudaz._engine._constructors import (
    query_paginated,
    search_paginated,
)
from nextlabs_sdk._cloudaz._engine._runner import SyncEndpointRunner
from nextlabs_sdk._cloudaz._engine._async_runner import AsyncEndpointRunner
from nextlabs_sdk._cloudaz._response import parse_data
from nextlabs_sdk._cloudaz._search import SavedSearch, SearchCriteria
from nextlabs_sdk._pagination import AsyncPaginator, SyncPaginator
from nextlabs_sdk.exceptions import raise_for_status

_SEARCH_SPEC = search_paginated(ComponentType, "/console/api/v1/policyModel/search")
_SAVED_SEARCHES_SPEC = query_paginated(
    SavedSearch,
    "/console/api/v1/policyModel/search/savedlist/{search_type}",
)
_FIND_SAVED_SEARCH_SPEC = query_paginated(
    SavedSearch,
    "/console/api/v1/policyModel/search/savedlist/{search_type}/{name}",
)

_SEARCH_TYPE_ARG = "search_type"


class ComponentTypeSearchService:

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._runner = SyncEndpointRunner(client)

    def search(self, criteria: SearchCriteria) -> SyncPaginator[ComponentType]:
        return self._runner.pages(_SEARCH_SPEC, {"criteria": criteria})

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
        return self._runner.pages(
            _SAVED_SEARCHES_SPEC,
            {_SEARCH_TYPE_ARG: search_type},
            page_size=page_size,
        )

    def find_saved_search(
        self,
        search_type: str,
        name: str,
        *,
        page_size: int | None = None,
    ) -> SyncPaginator[SavedSearch]:
        return self._runner.pages(
            _FIND_SAVED_SEARCH_SPEC,
            {_SEARCH_TYPE_ARG: search_type, "name": name},
            page_size=page_size,
        )


class AsyncComponentTypeSearchService:

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._runner = AsyncEndpointRunner(client)

    def search(self, criteria: SearchCriteria) -> AsyncPaginator[ComponentType]:
        return self._runner.pages(_SEARCH_SPEC, {"criteria": criteria})

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
        return self._runner.pages(
            _SAVED_SEARCHES_SPEC,
            {_SEARCH_TYPE_ARG: search_type},
            page_size=page_size,
        )

    def find_saved_search(
        self,
        search_type: str,
        name: str,
        *,
        page_size: int | None = None,
    ) -> AsyncPaginator[SavedSearch]:
        return self._runner.pages(
            _FIND_SAVED_SEARCH_SPEC,
            {_SEARCH_TYPE_ARG: search_type, "name": name},
            page_size=page_size,
        )
