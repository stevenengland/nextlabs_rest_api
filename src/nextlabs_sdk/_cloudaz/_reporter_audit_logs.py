from __future__ import annotations

import httpx

from nextlabs_sdk._cloudaz._engine._async_runner import AsyncEndpointRunner
from nextlabs_sdk._cloudaz._engine._constructors import query_paginated
from nextlabs_sdk._cloudaz._engine._dialect import PAGEABLE
from nextlabs_sdk._cloudaz._engine._runner import SyncEndpointRunner
from nextlabs_sdk._cloudaz._reporter_audit_log_models import ReporterAuditLogEntry
from nextlabs_sdk._pagination import AsyncPaginator, SyncPaginator

_SEARCH_SPEC = query_paginated(
    ReporterAuditLogEntry,
    "/nextlabs-reporter/api/activity-logs/search",
    dialect=PAGEABLE,
)


class ReporterAuditLogService:
    """Audit logs for Reporter components (Activity Reports, Monitors, Alerts)."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._runner = SyncEndpointRunner(client)

    def search(
        self,
        *,
        page_size: int = 20,
    ) -> SyncPaginator[ReporterAuditLogEntry]:
        """Search Reporter audit logs. Returns a paginator over entries."""
        return self._runner.pages(_SEARCH_SPEC, {}, page_size=page_size)


class AsyncReporterAuditLogService:
    """Async variant of :class:`ReporterAuditLogService`."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._runner = AsyncEndpointRunner(client)

    def search(
        self,
        *,
        page_size: int = 20,
    ) -> AsyncPaginator[ReporterAuditLogEntry]:
        """Search Reporter audit logs. Returns an async paginator over entries."""
        return self._runner.pages(_SEARCH_SPEC, {}, page_size=page_size)
