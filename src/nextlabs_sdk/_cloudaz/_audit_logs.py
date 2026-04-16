from __future__ import annotations

import functools

import httpx

from nextlabs_sdk._cloudaz._audit_log_models import (
    AuditLogEntry,
    AuditLogQuery,
    AuditLogUser,
    ExportAuditLogsRequest,
)
from nextlabs_sdk._cloudaz._response import parse_data, parse_reporter_paginated
from nextlabs_sdk._pagination import AsyncPaginator, PageResult, SyncPaginator
from nextlabs_sdk.exceptions import raise_for_status

_SEARCH_PATH = "/nextlabs-reporter/api/v1/auditLogs/search"
_EXPORT_PATH = "/nextlabs-reporter/api/v1/auditLogs/export"
_USERS_PATH = "/nextlabs-reporter/api/v1/auditLogs/users"


class EntityAuditLogService:

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def search(self, query: AuditLogQuery) -> SyncPaginator[AuditLogEntry]:
        return SyncPaginator(
            fetch_page=functools.partial(self._fetch_page, query),
        )

    def export(self, request: ExportAuditLogsRequest) -> bytes:
        payload = request.model_dump(by_alias=True, exclude_none=True)
        response = self._client.post(_EXPORT_PATH, json=payload)
        raise_for_status(response)
        return response.content

    def list_users(self) -> list[AuditLogUser]:
        response = self._client.get(_USERS_PATH)
        raw_users = parse_data(response)
        return [AuditLogUser.model_validate(entry) for entry in raw_users]

    def _fetch_page(
        self,
        query: AuditLogQuery,
        page_no: int,
    ) -> PageResult[AuditLogEntry]:
        page_query = query.model_copy(update={"page_number": page_no})
        payload = page_query.model_dump(by_alias=True, exclude_none=True)
        response = self._client.post(_SEARCH_PATH, json=payload)
        raw_items, total_pages, total_records = parse_reporter_paginated(response)
        entries = [AuditLogEntry.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=total_pages,
            total_records=total_records,
        )


class AsyncEntityAuditLogService:

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def search(self, query: AuditLogQuery) -> AsyncPaginator[AuditLogEntry]:
        return AsyncPaginator(
            fetch_page=functools.partial(self._fetch_page, query),
        )

    async def export(self, request: ExportAuditLogsRequest) -> bytes:
        payload = request.model_dump(by_alias=True, exclude_none=True)
        response = await self._client.post(_EXPORT_PATH, json=payload)
        raise_for_status(response)
        return response.content

    async def list_users(self) -> list[AuditLogUser]:
        response = await self._client.get(_USERS_PATH)
        raw_users = parse_data(response)
        return [AuditLogUser.model_validate(entry) for entry in raw_users]

    async def _fetch_page(
        self,
        query: AuditLogQuery,
        page_no: int,
    ) -> PageResult[AuditLogEntry]:
        page_query = query.model_copy(update={"page_number": page_no})
        payload = page_query.model_dump(by_alias=True, exclude_none=True)
        response = await self._client.post(_SEARCH_PATH, json=payload)
        raw_items, total_pages, total_records = parse_reporter_paginated(response)
        entries = [AuditLogEntry.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=total_pages,
            total_records=total_records,
        )
