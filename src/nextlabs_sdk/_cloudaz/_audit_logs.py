from __future__ import annotations

from dataclasses import dataclass, replace

import httpx

from nextlabs_sdk._cloudaz._audit_log_models import (
    AuditLogEntry,
    AuditLogQuery,
    AuditLogUser,
    ExportAuditLogsRequest,
)
from nextlabs_sdk._cloudaz._engine._async_runner import AsyncEndpointRunner
from nextlabs_sdk._cloudaz._engine._constructors import CRITERIA_ARG, search_paginated
from nextlabs_sdk._cloudaz._engine._dialect import REPORTER_ENVELOPE
from nextlabs_sdk._cloudaz._engine._runner import SyncEndpointRunner
from nextlabs_sdk._cloudaz._response import parse_data
from nextlabs_sdk._pagination import AsyncPaginator, SyncPaginator
from nextlabs_sdk.exceptions import raise_for_status

_SEARCH_PATH = "/nextlabs-reporter/api/v1/auditLogs/search"
_EXPORT_PATH = "/nextlabs-reporter/api/v1/auditLogs/export"
_USERS_PATH = "/nextlabs-reporter/api/v1/auditLogs/users"

_SEARCH_SPEC = search_paginated(
    AuditLogEntry,
    _SEARCH_PATH,
    dialect=REPORTER_ENVELOPE,
)


@dataclass(frozen=True)
class _AuditLogCriteria:
    """Adapts an ``AuditLogQuery`` to the engine's search-paging protocol."""

    query: AuditLogQuery
    page_no: int = 0

    def page(self, page_no: int) -> _AuditLogCriteria:
        return replace(self, page_no=page_no)

    def to_dict(self) -> dict[str, object]:
        page_query = self.query.model_copy(update={"page_number": self.page_no})
        return page_query.model_dump(by_alias=True, exclude_none=True)


class EntityAuditLogService:

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._runner = SyncEndpointRunner(client)

    def search(self, query: AuditLogQuery) -> SyncPaginator[AuditLogEntry]:
        return self._runner.pages(
            _SEARCH_SPEC,
            {CRITERIA_ARG: _AuditLogCriteria(query)},
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


class AsyncEntityAuditLogService:

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._runner = AsyncEndpointRunner(client)

    def search(self, query: AuditLogQuery) -> AsyncPaginator[AuditLogEntry]:
        return self._runner.pages(
            _SEARCH_SPEC,
            {CRITERIA_ARG: _AuditLogCriteria(query)},
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
