from __future__ import annotations

import httpx

from nextlabs_sdk._cloudaz._component_models import (
    ComponentLite,
    ComponentNameEntry,
)
from nextlabs_sdk._cloudaz._engine._constructors import (
    CRITERIA_ARG,
    query_paginated,
    search_paginated,
)
from nextlabs_sdk._cloudaz._engine._runner import SyncEndpointRunner
from nextlabs_sdk._cloudaz._engine._async_runner import AsyncEndpointRunner
from nextlabs_sdk._cloudaz._response import parse_data
from nextlabs_sdk._cloudaz._search import SavedSearch, SearchCriteria
from nextlabs_sdk._pagination import AsyncPaginator, SyncPaginator
from nextlabs_sdk.exceptions import raise_for_status

_SEARCH_SPEC = search_paginated(ComponentLite, "/console/api/v1/component/search")
_SAVED_SEARCHES_SPEC = query_paginated(
    SavedSearch,
    "/console/api/v1/component/search/savedlist",
)
_FIND_SAVED_SEARCH_SPEC = query_paginated(
    SavedSearch,
    "/console/api/v1/component/search/savedlist/{name}",
)
_LIST_NAMES_SPEC = query_paginated(
    ComponentNameEntry,
    "/console/api/v1/component/search/listNames/{group}",
)
_LIST_NAMES_BY_TYPE_SPEC = query_paginated(
    ComponentNameEntry,
    "/console/api/v1/component/search/listNames/{group}/{component_type}",
)

_GROUP_ARG = "group"
_COMPONENT_TYPE_ARG = "component_type"
_NAME_ARG = "name"


class ComponentSearchService:  # noqa: WPS214

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._runner = SyncEndpointRunner(client)

    def search(self, criteria: SearchCriteria) -> SyncPaginator[ComponentLite]:
        return self._runner.pages(_SEARCH_SPEC, {CRITERIA_ARG: criteria})

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
        return self._runner.pages(_SAVED_SEARCHES_SPEC, {}, page_size=page_size)

    def find_saved_search(
        self,
        name: str,
        *,
        page_size: int | None = None,
    ) -> SyncPaginator[SavedSearch]:
        return self._runner.pages(
            _FIND_SAVED_SEARCH_SPEC,
            {_NAME_ARG: name},
            page_size=page_size,
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
        return self._runner.pages(
            _LIST_NAMES_SPEC,
            {_GROUP_ARG: group},
            page_size=page_size,
        )

    def list_names_by_type(
        self,
        group: str,
        component_type: str,
        *,
        page_size: int | None = None,
    ) -> SyncPaginator[ComponentNameEntry]:
        return self._runner.pages(
            _LIST_NAMES_BY_TYPE_SPEC,
            {_GROUP_ARG: group, _COMPONENT_TYPE_ARG: component_type},
            page_size=page_size,
        )


class AsyncComponentSearchService:  # noqa: WPS214

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._runner = AsyncEndpointRunner(client)

    def search(self, criteria: SearchCriteria) -> AsyncPaginator[ComponentLite]:
        return self._runner.pages(_SEARCH_SPEC, {CRITERIA_ARG: criteria})

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
        return self._runner.pages(_SAVED_SEARCHES_SPEC, {}, page_size=page_size)

    def find_saved_search(
        self,
        name: str,
        *,
        page_size: int | None = None,
    ) -> AsyncPaginator[SavedSearch]:
        return self._runner.pages(
            _FIND_SAVED_SEARCH_SPEC,
            {_NAME_ARG: name},
            page_size=page_size,
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
        return self._runner.pages(
            _LIST_NAMES_SPEC,
            {_GROUP_ARG: group},
            page_size=page_size,
        )

    def list_names_by_type(
        self,
        group: str,
        component_type: str,
        *,
        page_size: int | None = None,
    ) -> AsyncPaginator[ComponentNameEntry]:
        return self._runner.pages(
            _LIST_NAMES_BY_TYPE_SPEC,
            {_GROUP_ARG: group, _COMPONENT_TYPE_ARG: component_type},
            page_size=page_size,
        )
