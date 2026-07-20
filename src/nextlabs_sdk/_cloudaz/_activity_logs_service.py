from __future__ import annotations

from dataclasses import dataclass, replace

import httpx

from nextlabs_sdk._cloudaz._activity_log_query_models import (
    ActivityLogAttribute,
    ActivityLogQuery,
)
from nextlabs_sdk._cloudaz._engine._async_runner import AsyncEndpointRunner
from nextlabs_sdk._cloudaz._engine._constructors import search_paginated
from nextlabs_sdk._cloudaz._engine._dialect import REPORTER_ENVELOPE
from nextlabs_sdk._cloudaz._engine._runner import SyncEndpointRunner
from nextlabs_sdk._cloudaz._report_models import EnforcementEntry
from nextlabs_sdk._cloudaz._response import parse_data
from nextlabs_sdk._pagination import AsyncPaginator, SyncPaginator
from nextlabs_sdk.exceptions import raise_for_status

_BASE_PATH = "/nextlabs-reporter/api/v1/report-activity-logs"

_SEARCH_SPEC = search_paginated(
    EnforcementEntry,
    _BASE_PATH,
    dialect=REPORTER_ENVELOPE,
)


@dataclass(frozen=True)
class _ActivityLogCriteria:
    """Adapts an ``ActivityLogQuery`` to the engine's search-paging protocol."""

    query: ActivityLogQuery
    page_size: int
    page_no: int = 0

    def page(self, page_no: int, page_size: int = 20) -> _ActivityLogCriteria:
        return replace(self, page_no=page_no)

    def to_dict(self) -> dict[str, object]:
        payload = self.query.model_dump(by_alias=True, exclude_none=True)
        payload["page"] = self.page_no
        payload["size"] = self.page_size
        return payload


class ReportActivityLogService:
    """Synchronous service for report activity log endpoints."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._runner = SyncEndpointRunner(client)

    def search(
        self,
        query: ActivityLogQuery,
        *,
        page_size: int = 20,
    ) -> SyncPaginator[EnforcementEntry]:
        """Search policy activity logs. Returns a paginator over EnforcementEntry."""
        return self._runner.pages(
            _SEARCH_SPEC,
            {"criteria": _ActivityLogCriteria(query, page_size)},
        )

    def get_by_row_id(self, row_id: int) -> list[ActivityLogAttribute]:
        """Retrieve full detail for a single activity log entry."""
        response = self._client.get(f"{_BASE_PATH}/{row_id}")
        raw = parse_data(response)
        return [ActivityLogAttribute.model_validate(entry) for entry in raw]

    def export(self, query: ActivityLogQuery) -> bytes:
        """Export activity logs matching query. Returns raw file bytes."""
        payload = query.model_dump(by_alias=True, exclude_none=True)
        response = self._client.post(f"{_BASE_PATH}/export", json=payload)
        raise_for_status(response)
        return response.content

    def export_by_row_id(self, row_id: int) -> bytes:
        """Export a single activity log entry. Returns raw file bytes."""
        response = self._client.post(f"{_BASE_PATH}/{row_id}/export")
        raise_for_status(response)
        return response.content


class AsyncReportActivityLogService:
    """Asynchronous service for report activity log endpoints."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._runner = AsyncEndpointRunner(client)

    def search(
        self,
        query: ActivityLogQuery,
        *,
        page_size: int = 20,
    ) -> AsyncPaginator[EnforcementEntry]:
        """Search policy activity logs. Returns an async paginator over EnforcementEntry."""
        return self._runner.pages(
            _SEARCH_SPEC,
            {"criteria": _ActivityLogCriteria(query, page_size)},
        )

    async def get_by_row_id(self, row_id: int) -> list[ActivityLogAttribute]:
        """Retrieve full detail for a single activity log entry."""
        response = await self._client.get(f"{_BASE_PATH}/{row_id}")
        raw = parse_data(response)
        return [ActivityLogAttribute.model_validate(entry) for entry in raw]

    async def export(self, query: ActivityLogQuery) -> bytes:
        """Export activity logs matching query. Returns raw file bytes."""
        payload = query.model_dump(by_alias=True, exclude_none=True)
        response = await self._client.post(f"{_BASE_PATH}/export", json=payload)
        raise_for_status(response)
        return response.content

    async def export_by_row_id(self, row_id: int) -> bytes:
        """Export a single activity log entry. Returns raw file bytes."""
        response = await self._client.post(f"{_BASE_PATH}/{row_id}/export")
        raise_for_status(response)
        return response.content
