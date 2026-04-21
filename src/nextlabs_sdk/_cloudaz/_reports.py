from __future__ import annotations

import builtins
import functools

import httpx
from pydantic import BaseModel

from nextlabs_sdk._cloudaz._report_models import (
    ApplicationUser,
    AttributeMappings,
    CachedPolicy,
    CachedUser,
    DeleteReportsRequest,
    EnforcementEntry,
    PolicyActivityReport,
    PolicyActivityReportDetail,
    PolicyActivityReportRequest,
    ResourceActions,
    UserGroup,
    WidgetData,
)
from nextlabs_sdk._cloudaz._response import parse_data, parse_reporter_paginated
from nextlabs_sdk._pagination import AsyncPaginator, PageResult, SyncPaginator
from nextlabs_sdk.exceptions import raise_for_status

_BASE_PATH = "/nextlabs-reporter/api/v1/policy-activity-reports"

_FIELD_TITLE = "title"
_FIELD_SORT_BY = "sortBy"
_FIELD_SORT_ORDER = "sortOrder"
_FIELD_PAGE = "page"
_FIELD_SIZE = "size"
_SORT_ORDER_ASCENDING = "ascending"
_SORT_FIELD_ROW_ID = "rowId"


class PolicyActivityReportService:

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    # --- CRUD ---

    def list(  # noqa: WPS125
        self,
        *,
        title: str = "",
        is_shared: bool = True,
        policy_decision: str = "AD",
        sort_by: str = _FIELD_TITLE,
        sort_order: str = _SORT_ORDER_ASCENDING,
        page_size: int = 20,
    ) -> SyncPaginator[PolicyActivityReport]:
        """List policy activity reports."""
        return SyncPaginator(
            fetch_page=functools.partial(
                self._fetch_list_page,
                title,
                is_shared,
                policy_decision,
                sort_by,
                sort_order,
                page_size,
            ),
        )

    def get(self, report_id: int) -> PolicyActivityReportDetail:
        """Retrieve a report's criteria and widget configuration."""
        response = self._client.get(f"{_BASE_PATH}/{report_id}")
        raw = parse_data(response)
        return PolicyActivityReportDetail.model_validate(raw)

    def create(self, request: PolicyActivityReportRequest) -> PolicyActivityReport:
        """Create a new policy activity report."""
        payload = self._payload(request)
        response = self._client.post(_BASE_PATH, json=payload)
        raw = parse_data(response)
        return PolicyActivityReport.model_validate(raw)

    def modify(
        self, report_id: int, request: PolicyActivityReportRequest
    ) -> PolicyActivityReport:
        """Modify an existing policy activity report."""
        payload = self._payload(request)
        response = self._client.put(f"{_BASE_PATH}/{report_id}", json=payload)
        raw = parse_data(response)
        return PolicyActivityReport.model_validate(raw)

    def delete(self, request: DeleteReportsRequest) -> None:
        """Delete reports by IDs or query parameters."""
        payload = self._payload(request)
        response = self._client.post(f"{_BASE_PATH}/delete", json=payload)
        raise_for_status(response)

    # --- Saved report data ---

    def get_widgets(self, report_id: int) -> WidgetData:
        """Retrieve widget data for a saved report."""
        response = self._client.get(f"{_BASE_PATH}/{report_id}/widgets")
        raw = parse_data(response)
        return WidgetData.model_validate(raw)

    def get_enforcements(
        self,
        report_id: int,
        *,
        sort_by: str = _SORT_FIELD_ROW_ID,
        sort_order: str = _SORT_ORDER_ASCENDING,
        page_size: int = 20,
    ) -> SyncPaginator[EnforcementEntry]:
        """Retrieve enforcement logs for a saved report."""
        return SyncPaginator(
            fetch_page=functools.partial(
                self._fetch_enforcement_page,
                report_id,
                sort_by,
                sort_order,
                page_size,
            ),
        )

    def export(
        self,
        report_id: int,
        *,
        sort_by: str = _SORT_FIELD_ROW_ID,
        sort_order: str = _SORT_ORDER_ASCENDING,
    ) -> bytes:
        """Export enforcement logs for a saved report."""
        query_params = {_FIELD_SORT_BY: sort_by, _FIELD_SORT_ORDER: sort_order}
        response = self._client.post(
            f"{_BASE_PATH}/{report_id}/export", params=query_params
        )
        raise_for_status(response)
        return response.content

    # --- Ad-hoc generate ---

    def generate_widgets(self, request: PolicyActivityReportRequest) -> WidgetData:
        """Generate widget data for ad-hoc criteria."""
        payload = self._payload(request)
        response = self._client.post(f"{_BASE_PATH}/generate/widgets", json=payload)
        raw = parse_data(response)
        return WidgetData.model_validate(raw)

    def generate_enforcements(
        self,
        request: PolicyActivityReportRequest,
        *,
        sort_by: str = _SORT_FIELD_ROW_ID,
        sort_order: str = _SORT_ORDER_ASCENDING,
        page_size: int = 20,
    ) -> SyncPaginator[EnforcementEntry]:
        """Generate enforcement logs for ad-hoc criteria."""
        return SyncPaginator(
            fetch_page=functools.partial(
                self._fetch_generate_enforcement_page,
                request,
                sort_by,
                sort_order,
                page_size,
            ),
        )

    def generate_export(
        self,
        request: PolicyActivityReportRequest,
        *,
        sort_by: str = _SORT_FIELD_ROW_ID,
        sort_order: str = _SORT_ORDER_ASCENDING,
    ) -> bytes:
        """Export enforcement logs for ad-hoc criteria."""
        payload = self._payload(request)
        query_params = {_FIELD_SORT_BY: sort_by, _FIELD_SORT_ORDER: sort_order}
        response = self._client.post(
            f"{_BASE_PATH}/generate/export", json=payload, params=query_params
        )
        raise_for_status(response)
        return response.content

    # --- Cached data ---

    def list_cached_users(self) -> builtins.list[CachedUser]:
        """Retrieve cached enforcement users."""
        response = self._client.get(f"{_BASE_PATH}/users")
        raw = parse_data(response)
        return [CachedUser.model_validate(entry) for entry in raw]

    def list_cached_policies(self) -> builtins.list[CachedPolicy]:
        """Retrieve cached policies."""
        response = self._client.get(f"{_BASE_PATH}/policies")
        raw = parse_data(response)
        return [CachedPolicy.model_validate(entry) for entry in raw]

    def get_resource_actions(self) -> ResourceActions:
        """Retrieve policy models with their available actions."""
        response = self._client.get(f"{_BASE_PATH}/resource-actions")
        raw = parse_data(response)
        return ResourceActions.model_validate(raw)

    def get_mappings(self) -> AttributeMappings:
        """Retrieve attribute-to-column mappings."""
        response = self._client.get(f"{_BASE_PATH}/mappings")
        raw = parse_data(response)
        return AttributeMappings.model_validate(raw)

    # --- Sharing ---

    def list_user_groups(self) -> builtins.list[UserGroup]:
        """Retrieve user groups available for report sharing."""
        response = self._client.get(f"{_BASE_PATH}/share/user-groups")
        raw = parse_data(response)
        return [UserGroup.model_validate(entry) for entry in raw]

    def list_application_users(self) -> builtins.list[ApplicationUser]:
        """Retrieve application users available for report sharing."""
        response = self._client.get(f"{_BASE_PATH}/share/application-users")
        raw = parse_data(response)
        return [ApplicationUser.model_validate(entry) for entry in raw]

    # --- Internal pagination callbacks ---

    def _payload(self, request: BaseModel) -> dict[str, object]:
        return request.model_dump(by_alias=True, exclude_none=True)

    def _fetch_list_page(
        self,
        title: str,
        is_shared: bool,
        policy_decision: str,
        sort_by: str,
        sort_order: str,
        page_size: int,
        page_no: int,
    ) -> PageResult[PolicyActivityReport]:
        query_params: dict[str, str | int | bool] = {
            _FIELD_TITLE: title,
            "isShared": is_shared,
            "policyDecision": policy_decision,
            _FIELD_SORT_BY: sort_by,
            _FIELD_SORT_ORDER: sort_order,
            _FIELD_SIZE: page_size,
            _FIELD_PAGE: page_no,
        }
        response = self._client.get(_BASE_PATH, params=query_params)
        raw_items, total_pages, total_records = parse_reporter_paginated(response)
        reports = [
            PolicyActivityReport.model_validate(raw_item) for raw_item in raw_items
        ]
        return PageResult(
            entries=reports,
            page_no=page_no,
            page_size=len(reports),
            total_pages=total_pages,
            total_records=total_records,
        )

    def _fetch_enforcement_page(
        self,
        report_id: int,
        sort_by: str,
        sort_order: str,
        page_size: int,
        page_no: int,
    ) -> PageResult[EnforcementEntry]:
        query_params: dict[str, str | int] = {
            _FIELD_PAGE: page_no,
            _FIELD_SIZE: page_size,
            _FIELD_SORT_BY: sort_by,
            _FIELD_SORT_ORDER: sort_order,
        }
        response = self._client.get(
            f"{_BASE_PATH}/{report_id}/enforcements", params=query_params
        )
        raw_items, total_pages, total_records = parse_reporter_paginated(response)
        entries = [EnforcementEntry.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=total_pages,
            total_records=total_records,
        )

    def _fetch_generate_enforcement_page(
        self,
        request: PolicyActivityReportRequest,
        sort_by: str,
        sort_order: str,
        page_size: int,
        page_no: int,
    ) -> PageResult[EnforcementEntry]:
        payload = self._payload(request)
        query_params: dict[str, str | int] = {
            _FIELD_PAGE: page_no,
            _FIELD_SIZE: page_size,
            _FIELD_SORT_BY: sort_by,
            _FIELD_SORT_ORDER: sort_order,
        }
        response = self._client.post(
            f"{_BASE_PATH}/generate/enforcements",
            json=payload,
            params=query_params,
        )
        raw_items, total_pages, total_records = parse_reporter_paginated(response)
        entries = [EnforcementEntry.model_validate(entry) for entry in raw_items]
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=total_pages,
            total_records=total_records,
        )


class AsyncPolicyActivityReportService:

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    # --- CRUD ---

    def list(  # noqa: WPS125
        self,
        *,
        title: str = "",
        is_shared: bool = True,
        policy_decision: str = "AD",
        sort_by: str = _FIELD_TITLE,
        sort_order: str = _SORT_ORDER_ASCENDING,
        page_size: int = 20,
    ) -> AsyncPaginator[PolicyActivityReport]:
        """List policy activity reports."""
        return AsyncPaginator(
            fetch_page=functools.partial(
                self._fetch_list_page,
                title,
                is_shared,
                policy_decision,
                sort_by,
                sort_order,
                page_size,
            ),
        )

    async def get(self, report_id: int) -> PolicyActivityReportDetail:
        """Retrieve a report's criteria and widget configuration."""
        response = await self._client.get(f"{_BASE_PATH}/{report_id}")
        raw = parse_data(response)
        return PolicyActivityReportDetail.model_validate(raw)

    async def create(
        self, request: PolicyActivityReportRequest
    ) -> PolicyActivityReport:
        """Create a new policy activity report."""
        payload = self._payload(request)
        response = await self._client.post(_BASE_PATH, json=payload)
        raw = parse_data(response)
        return PolicyActivityReport.model_validate(raw)

    async def modify(
        self, report_id: int, request: PolicyActivityReportRequest
    ) -> PolicyActivityReport:
        """Modify an existing policy activity report."""
        payload = self._payload(request)
        response = await self._client.put(f"{_BASE_PATH}/{report_id}", json=payload)
        raw = parse_data(response)
        return PolicyActivityReport.model_validate(raw)

    async def delete(self, request: DeleteReportsRequest) -> None:
        """Delete reports by IDs or query parameters."""
        payload = self._payload(request)
        response = await self._client.post(f"{_BASE_PATH}/delete", json=payload)
        raise_for_status(response)

    # --- Saved report data ---

    async def get_widgets(self, report_id: int) -> WidgetData:
        """Retrieve widget data for a saved report."""
        response = await self._client.get(f"{_BASE_PATH}/{report_id}/widgets")
        raw = parse_data(response)
        return WidgetData.model_validate(raw)

    def get_enforcements(
        self,
        report_id: int,
        *,
        sort_by: str = _SORT_FIELD_ROW_ID,
        sort_order: str = _SORT_ORDER_ASCENDING,
        page_size: int = 20,
    ) -> AsyncPaginator[EnforcementEntry]:
        """Retrieve enforcement logs for a saved report."""
        return AsyncPaginator(
            fetch_page=functools.partial(
                self._fetch_enforcement_page,
                report_id,
                sort_by,
                sort_order,
                page_size,
            ),
        )

    async def export(
        self,
        report_id: int,
        *,
        sort_by: str = _SORT_FIELD_ROW_ID,
        sort_order: str = _SORT_ORDER_ASCENDING,
    ) -> bytes:
        """Export enforcement logs for a saved report. Returns raw file bytes."""
        query_params = {_FIELD_SORT_BY: sort_by, _FIELD_SORT_ORDER: sort_order}
        response = await self._client.post(
            f"{_BASE_PATH}/{report_id}/export", params=query_params
        )
        raise_for_status(response)
        return response.content

    # --- Ad-hoc generate ---

    async def generate_widgets(
        self, request: PolicyActivityReportRequest
    ) -> WidgetData:
        """Generate widget data for ad-hoc criteria."""
        payload = self._payload(request)
        response = await self._client.post(
            f"{_BASE_PATH}/generate/widgets", json=payload
        )
        raw = parse_data(response)
        return WidgetData.model_validate(raw)

    def generate_enforcements(
        self,
        request: PolicyActivityReportRequest,
        *,
        sort_by: str = _SORT_FIELD_ROW_ID,
        sort_order: str = _SORT_ORDER_ASCENDING,
        page_size: int = 20,
    ) -> AsyncPaginator[EnforcementEntry]:
        """Generate enforcement logs for ad-hoc criteria."""
        return AsyncPaginator(
            fetch_page=functools.partial(
                self._fetch_generate_enforcement_page,
                request,
                sort_by,
                sort_order,
                page_size,
            ),
        )

    async def generate_export(
        self,
        request: PolicyActivityReportRequest,
        *,
        sort_by: str = _SORT_FIELD_ROW_ID,
        sort_order: str = _SORT_ORDER_ASCENDING,
    ) -> bytes:
        """Export enforcement logs for ad-hoc criteria. Returns raw file bytes."""
        payload = self._payload(request)
        query_params = {_FIELD_SORT_BY: sort_by, _FIELD_SORT_ORDER: sort_order}
        response = await self._client.post(
            f"{_BASE_PATH}/generate/export", json=payload, params=query_params
        )
        raise_for_status(response)
        return response.content

    # --- Cached data ---

    async def list_cached_users(self) -> builtins.list[CachedUser]:
        """Retrieve cached enforcement users."""
        response = await self._client.get(f"{_BASE_PATH}/users")
        raw = parse_data(response)
        return [CachedUser.model_validate(raw_item) for raw_item in raw]

    async def list_cached_policies(self) -> builtins.list[CachedPolicy]:
        """Retrieve cached policies."""
        response = await self._client.get(f"{_BASE_PATH}/policies")
        raw = parse_data(response)
        return [CachedPolicy.model_validate(raw_item) for raw_item in raw]

    async def get_resource_actions(self) -> ResourceActions:
        """Retrieve policy models with their available actions."""
        response = await self._client.get(f"{_BASE_PATH}/resource-actions")
        raw = parse_data(response)
        return ResourceActions.model_validate(raw)

    async def get_mappings(self) -> AttributeMappings:
        """Retrieve attribute-to-column mappings."""
        response = await self._client.get(f"{_BASE_PATH}/mappings")
        raw = parse_data(response)
        return AttributeMappings.model_validate(raw)

    # --- Sharing ---

    async def list_user_groups(self) -> builtins.list[UserGroup]:
        """Retrieve user groups available for report sharing."""
        response = await self._client.get(f"{_BASE_PATH}/share/user-groups")
        raw = parse_data(response)
        return [UserGroup.model_validate(raw_item) for raw_item in raw]

    async def list_application_users(self) -> builtins.list[ApplicationUser]:
        """Retrieve application users available for report sharing."""
        response = await self._client.get(f"{_BASE_PATH}/share/application-users")
        raw = parse_data(response)
        return [ApplicationUser.model_validate(raw_item) for raw_item in raw]

    # --- Internal pagination callbacks ---

    def _payload(self, request: BaseModel) -> dict[str, object]:
        return request.model_dump(by_alias=True, exclude_none=True)

    async def _fetch_list_page(
        self,
        title: str,
        is_shared: bool,
        policy_decision: str,
        sort_by: str,
        sort_order: str,
        page_size: int,
        page_no: int,
    ) -> PageResult[PolicyActivityReport]:
        query_params: dict[str, str | int | bool] = {
            _FIELD_TITLE: title,
            "isShared": is_shared,
            "policyDecision": policy_decision,
            _FIELD_SORT_BY: sort_by,
            _FIELD_SORT_ORDER: sort_order,
            _FIELD_SIZE: page_size,
            _FIELD_PAGE: page_no,
        }
        response = await self._client.get(_BASE_PATH, params=query_params)
        raw_items, total_pages, total_records = parse_reporter_paginated(response)
        reports = [
            PolicyActivityReport.model_validate(raw_item) for raw_item in raw_items
        ]
        return PageResult(
            entries=reports,
            page_no=page_no,
            page_size=len(reports),
            total_pages=total_pages,
            total_records=total_records,
        )

    async def _fetch_enforcement_page(
        self,
        report_id: int,
        sort_by: str,
        sort_order: str,
        page_size: int,
        page_no: int,
    ) -> PageResult[EnforcementEntry]:
        query_params: dict[str, str | int | bool] = {
            _FIELD_PAGE: page_no,
            _FIELD_SIZE: page_size,
            _FIELD_SORT_BY: sort_by,
            _FIELD_SORT_ORDER: sort_order,
        }
        response = await self._client.get(
            f"{_BASE_PATH}/{report_id}/enforcements", params=query_params
        )
        raw_items, total_pages, total_records = parse_reporter_paginated(response)
        entries = [EnforcementEntry.model_validate(raw_item) for raw_item in raw_items]
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=total_pages,
            total_records=total_records,
        )

    async def _fetch_generate_enforcement_page(
        self,
        request: PolicyActivityReportRequest,
        sort_by: str,
        sort_order: str,
        page_size: int,
        page_no: int,
    ) -> PageResult[EnforcementEntry]:
        payload = self._payload(request)
        query_params: dict[str, str | int | bool] = {
            _FIELD_PAGE: page_no,
            _FIELD_SIZE: page_size,
            _FIELD_SORT_BY: sort_by,
            _FIELD_SORT_ORDER: sort_order,
        }
        response = await self._client.post(
            f"{_BASE_PATH}/generate/enforcements",
            json=payload,
            params=query_params,
        )
        raw_items, total_pages, total_records = parse_reporter_paginated(response)
        entries = [EnforcementEntry.model_validate(raw_item) for raw_item in raw_items]
        return PageResult(
            entries=entries,
            page_no=page_no,
            page_size=len(entries),
            total_pages=total_pages,
            total_records=total_records,
        )
