from __future__ import annotations

import functools

import httpx

from nextlabs_sdk._cloudaz._activity_log_query_models import (
    ActivityLogAttribute,
    ActivityLogQuery,
)
from nextlabs_sdk._cloudaz._report_models import EnforcementEntry
from nextlabs_sdk._cloudaz._response import parse_data, parse_reporter_paginated
from nextlabs_sdk._pagination import PageResult, SyncPaginator
from nextlabs_sdk.exceptions import raise_for_status

_BASE_PATH = "/nextlabs-reporter/api/v1/report-activity-logs"


class ReportActivityLogService:
    """Synchronous service for report activity log endpoints."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def search(
        self,
        query: ActivityLogQuery,
        *,
        page_size: int = 20,
    ) -> SyncPaginator[EnforcementEntry]:
        """Search policy activity logs. Returns a paginator over EnforcementEntry."""
        return SyncPaginator(
            fetch_page=functools.partial(
                self._fetch_search_page,
                query,
                page_size,
            ),
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

    def _fetch_search_page(
        self,
        query: ActivityLogQuery,
        page_size: int,
        page_no: int,
    ) -> PageResult[EnforcementEntry]:
        payload = query.model_dump(by_alias=True, exclude_none=True)
        payload["page"] = page_no
        payload["size"] = page_size
        response = self._client.post(_BASE_PATH, json=payload)
        raw_items, total_pages, total_records = parse_reporter_paginated(response)
        entries = [EnforcementEntry.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=total_pages,
            total_records=total_records,
        )
