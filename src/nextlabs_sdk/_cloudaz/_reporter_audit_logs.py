from __future__ import annotations

import functools

import httpx

from nextlabs_sdk._cloudaz._reporter_audit_log_models import ReporterAuditLogEntry
from nextlabs_sdk._cloudaz._response import parse_pageable
from nextlabs_sdk._pagination import AsyncPaginator, PageResult, SyncPaginator

_SEARCH_PATH = "/nextlabs-reporter/api/activity-logs/search"


class ReporterAuditLogService:
    """Audit logs for Reporter components (Activity Reports, Monitors, Alerts)."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def search(
        self,
        *,
        page_size: int = 20,
    ) -> SyncPaginator[ReporterAuditLogEntry]:
        """Search Reporter audit logs. Returns a paginator over entries."""
        return SyncPaginator(
            fetch_page=functools.partial(self._fetch_page, page_size),
        )

    def _fetch_page(
        self,
        page_size: int,
        page_no: int,
    ) -> PageResult[ReporterAuditLogEntry]:
        response = self._client.get(
            _SEARCH_PATH,
            params={"page": page_no, "size": page_size},
        )
        raw_items, total_pages, total_records = parse_pageable(response)
        entries = [ReporterAuditLogEntry.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=total_pages,
            total_records=total_records,
        )


class AsyncReporterAuditLogService:
    """Async variant of :class:`ReporterAuditLogService`."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def search(
        self,
        *,
        page_size: int = 20,
    ) -> AsyncPaginator[ReporterAuditLogEntry]:
        """Search Reporter audit logs. Returns an async paginator over entries."""
        return AsyncPaginator(
            fetch_page=functools.partial(self._fetch_page, page_size),
        )

    async def _fetch_page(
        self,
        page_size: int,
        page_no: int,
    ) -> PageResult[ReporterAuditLogEntry]:
        response = await self._client.get(
            _SEARCH_PATH,
            params={"page": page_no, "size": page_size},
        )
        raw_items, total_pages, total_records = parse_pageable(response)
        entries = [ReporterAuditLogEntry.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=total_pages,
            total_records=total_records,
        )
