from __future__ import annotations

import asyncio

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._report_models import (
    ApplicationUser,
    AttributeMappings,
    CachedPolicy,
    CachedUser,
    DeleteReportsRequest,
    EnforcementEntry,
    PolicyActivityReport,
    PolicyActivityReportDetail,
)
from nextlabs_sdk._cloudaz._report_models import (
    PolicyActivityReportRequest,
    ReportCriteria,
    ReportFilterGeneral,
    ReportFilters,
    ReportWidget,
    ResourceActions,
    UserGroup,
    WidgetData,
)
from nextlabs_sdk._cloudaz._reports import AsyncPolicyActivityReportService
from nextlabs_sdk._pagination import AsyncPaginator
from nextlabs_sdk.exceptions import ServerError

BASE_URL = "https://cloudaz.example.com"
_BASE_PATH = "/nextlabs-reporter/api/v1/policy-activity-reports"


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("POST", f"{BASE_URL}{path}")


def _make_reporter_envelope(
    content: list[object],
    total_pages: int = 1,
    total_elements: int = 1,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": {
                "content": content,
                "totalPages": total_pages,
                "totalElements": total_elements,
            },
        },
        request=_make_request(),
    )


def _make_data_envelope(data: object) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": data,
        },
        request=_make_request(),
    )


def _make_report_summary() -> dict[str, object]:
    return {
        "id": 8,
        "title": "Allow Enforcement in Last 7 Days",
        "description": "desc",
        "sharedMode": "public",
        "decision": "A",
        "dateMode": "Relative",
        "windowMode": "last_7_days",
        "startDate": "2024-08-14T03:05:16.148+00:00",
        "endDate": "2024-08-21T03:05:16.148+00:00",
        "lastUpdatedDate": "2024-08-18T02:17:23.484+00:00",
        "type": "report",
    }


def _make_simple_request() -> PolicyActivityReportRequest:
    return PolicyActivityReportRequest(
        criteria=ReportCriteria(
            filters=ReportFilters(
                general=ReportFilterGeneral(type="custom", date_mode="fixed"),
            ),
        ),
        widgets=[
            ReportWidget(
                name="enforcement",
                title="Trend",
                chart_type="line",
                attribute_name="decision",
            ),
        ],
    )


def _make_enforcement_data() -> dict[str, object]:
    return {
        "POLICY_NAME": "Encryption Policy",
        "ACTION": "SELECT",
        "FROM_RESOURCE_NAME": "file1.txt",
        "TIME": "2024-10-07T07:26:14.556+00:00",
        "USER_NAME": "user@example.com",
        "ACTION_SHORT_CODE": "e3",
        "ROW_ID": 2,
        "POLICY_DECISION": "A",
    }


# --- list ---


def test_async_list_returns_paginator() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    response = _make_reporter_envelope(content=[_make_report_summary()])
    when(client).get(
        _BASE_PATH,
        params={
            "title": "",
            "isShared": True,
            "policyDecision": "AD",
            "sortBy": "title",
            "sortOrder": "ascending",
            "size": 20,
            "page": 0,
        },
    ).thenReturn(response)

    paginator = service.list()
    assert isinstance(paginator, AsyncPaginator)

    async def collect() -> list[PolicyActivityReport]:
        return [r async for r in paginator]

    reports = asyncio.run(collect())
    assert len(reports) == 1
    assert reports[0].id == 8


def test_async_list_multi_page() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    r1 = _make_report_summary()
    r1["id"] = 1
    r2 = _make_report_summary()
    r2["id"] = 2

    when(client).get(
        _BASE_PATH,
        params={
            "title": "",
            "isShared": True,
            "policyDecision": "AD",
            "sortBy": "title",
            "sortOrder": "ascending",
            "size": 20,
            "page": 0,
        },
    ).thenReturn(_make_reporter_envelope(content=[r1], total_pages=2, total_elements=2))
    when(client).get(
        _BASE_PATH,
        params={
            "title": "",
            "isShared": True,
            "policyDecision": "AD",
            "sortBy": "title",
            "sortOrder": "ascending",
            "size": 20,
            "page": 1,
        },
    ).thenReturn(_make_reporter_envelope(content=[r2], total_pages=2, total_elements=2))

    async def collect() -> list[PolicyActivityReport]:
        return [r async for r in service.list()]

    reports = asyncio.run(collect())
    assert len(reports) == 2
    assert reports[0].id == 1
    assert reports[1].id == 2


# --- get ---


def test_async_get_returns_detail() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    response = _make_data_envelope(
        data={
            "criteria": {"filters": {"general": {"type": "custom"}}, "pagesize": 20},
            "widgets": [
                {
                    "id": 1,
                    "name": "e",
                    "title": "T",
                    "chartType": "line",
                    "attributeName": "d",
                    "maxSize": 10,
                }
            ],
        },
    )
    when(client).get(f"{_BASE_PATH}/42").thenReturn(response)

    async def run() -> PolicyActivityReportDetail:
        return await service.get(42)

    detail = asyncio.run(run())
    assert detail.criteria.filters is not None
    assert detail.criteria.filters.general is not None
    assert detail.criteria.filters.general.type == "custom"


# --- create ---


def test_async_create_returns_summary() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    request = _make_simple_request()
    response = _make_data_envelope(data=_make_report_summary())
    when(client).post(
        _BASE_PATH,
        json=request.model_dump(by_alias=True, exclude_none=True),
    ).thenReturn(response)

    async def run() -> PolicyActivityReport:
        return await service.create(request)

    report = asyncio.run(run())
    assert report.id == 8


# --- modify ---


def test_async_modify_returns_summary() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    request = _make_simple_request()
    response = _make_data_envelope(data=_make_report_summary())
    when(client).put(
        f"{_BASE_PATH}/42",
        json=request.model_dump(by_alias=True, exclude_none=True),
    ).thenReturn(response)

    async def run() -> PolicyActivityReport:
        return await service.modify(42, request)

    report = asyncio.run(run())
    assert report.id == 8


# --- delete ---


def test_async_delete_by_ids() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    request = DeleteReportsRequest(report_ids=[5, 10])
    response = httpx.Response(
        200, json={"statusCode": "1002", "message": "ok"}, request=_make_request()
    )
    when(client).post(f"{_BASE_PATH}/delete", json={"reportIds": [5, 10]}).thenReturn(
        response
    )

    async def run() -> None:
        await service.delete(request)

    asyncio.run(run())


def test_async_delete_raises_on_error() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    request = DeleteReportsRequest(report_ids=[999])
    response = httpx.Response(500, json={"message": "error"}, request=_make_request())
    when(client).post(f"{_BASE_PATH}/delete", json={"reportIds": [999]}).thenReturn(
        response
    )

    async def run() -> None:
        await service.delete(request)

    with pytest.raises(ServerError):
        asyncio.run(run())


# --- get_widgets ---


def test_async_get_widgets() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    response = _make_data_envelope(
        data={
            "enforcements": [
                {"hour": 100, "allowCount": 1, "denyCount": 0, "decisionCount": 1}
            ]
        },
    )
    when(client).get(f"{_BASE_PATH}/42/widgets").thenReturn(response)

    async def run() -> WidgetData:
        return await service.get_widgets(42)

    data = asyncio.run(run())
    assert len(data.enforcements) == 1


# --- get_enforcements ---


def test_async_get_enforcements() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    response = _make_reporter_envelope(content=[_make_enforcement_data()])
    when(client).get(
        f"{_BASE_PATH}/42/enforcements",
        params={"page": 0, "size": 20, "sortBy": "rowId", "sortOrder": "ascending"},
    ).thenReturn(response)

    async def collect() -> list[EnforcementEntry]:
        return [e async for e in service.get_enforcements(42)]

    entries = asyncio.run(collect())
    assert len(entries) == 1
    assert entries[0].row_id == 2


# --- export ---


def test_async_export_returns_bytes() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    csv = b"data"
    response = httpx.Response(200, content=csv, request=_make_request())
    when(client).post(
        f"{_BASE_PATH}/42/export",
        params={"sortBy": "rowId", "sortOrder": "ascending"},
    ).thenReturn(response)

    async def run() -> bytes:
        return await service.export(42)

    assert asyncio.run(run()) == csv


# --- generate_widgets ---


def test_async_generate_widgets() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    request = _make_simple_request()
    response = _make_data_envelope(
        data={
            "enforcements": [
                {"hour": 100, "allowCount": 0, "denyCount": 0, "decisionCount": 0}
            ]
        },
    )
    when(client).post(
        f"{_BASE_PATH}/generate/widgets",
        json=request.model_dump(by_alias=True, exclude_none=True),
    ).thenReturn(response)

    async def run() -> WidgetData:
        return await service.generate_widgets(request)

    data = asyncio.run(run())
    assert len(data.enforcements) == 1


# --- generate_enforcements ---


def test_async_generate_enforcements() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    request = _make_simple_request()
    payload = request.model_dump(by_alias=True, exclude_none=True)
    response = _make_reporter_envelope(content=[_make_enforcement_data()])
    when(client).post(
        f"{_BASE_PATH}/generate/enforcements",
        json=payload,
        params={"page": 0, "size": 20, "sortBy": "rowId", "sortOrder": "ascending"},
    ).thenReturn(response)

    async def collect() -> list[EnforcementEntry]:
        return [e async for e in service.generate_enforcements(request)]

    entries = asyncio.run(collect())
    assert len(entries) == 1


# --- generate_export ---


def test_async_generate_export() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    request = _make_simple_request()
    payload = request.model_dump(by_alias=True, exclude_none=True)
    csv = b"exported"
    response = httpx.Response(200, content=csv, request=_make_request())
    when(client).post(
        f"{_BASE_PATH}/generate/export",
        json=payload,
        params={"sortBy": "rowId", "sortOrder": "ascending"},
    ).thenReturn(response)

    async def run() -> bytes:
        return await service.generate_export(request)

    assert asyncio.run(run()) == csv


# --- Cached data ---


def test_async_list_cached_users() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    response = _make_data_envelope(
        data=[{"displayName": "test@localhost", "firstName": "T", "lastName": "U"}],
    )
    when(client).get(f"{_BASE_PATH}/users").thenReturn(response)

    async def run() -> list[CachedUser]:
        return await service.list_cached_users()

    users = asyncio.run(run())
    assert len(users) == 1


def test_async_list_cached_policies() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    response = _make_data_envelope(
        data=[{"name": "P", "fullName": "/ROOT/P"}],
    )
    when(client).get(f"{_BASE_PATH}/policies").thenReturn(response)

    async def run() -> list[CachedPolicy]:
        return await service.list_cached_policies()

    policies = asyncio.run(run())
    assert len(policies) == 1


def test_async_get_resource_actions() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    response = _make_data_envelope(
        data={
            "policyModelActions": {
                "t": [{"policyModelId": 1, "label": "a", "shortCode": "x"}]
            }
        },
    )
    when(client).get(f"{_BASE_PATH}/resource-actions").thenReturn(response)

    async def run() -> ResourceActions:
        return await service.get_resource_actions()

    result = asyncio.run(run())
    assert "t" in result.policy_model_actions


def test_async_get_mappings() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    response = _make_data_envelope(
        data={
            "resource": [
                {
                    "id": 1,
                    "name": "N",
                    "mappedColumn": "N",
                    "dataType": "STRING",
                    "attrType": "RESOURCE",
                    "isDynamic": False,
                }
            ],
            "user": [
                {
                    "id": 2,
                    "name": "U",
                    "mappedColumn": "U",
                    "dataType": "STRING",
                    "attrType": "USER",
                    "isDynamic": False,
                }
            ],
            "others": [
                {
                    "id": 3,
                    "name": "O",
                    "mappedColumn": "O",
                    "dataType": "STRING",
                    "attrType": "OTHERS",
                    "isDynamic": False,
                }
            ],
        },
    )
    when(client).get(f"{_BASE_PATH}/mappings").thenReturn(response)

    async def run() -> AttributeMappings:
        return await service.get_mappings()

    result = asyncio.run(run())
    assert len(result.resource) == 1


# --- Sharing ---


def test_async_list_user_groups() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    response = _make_data_envelope(data=[{"title": "Group", "id": 1}])
    when(client).get(f"{_BASE_PATH}/share/user-groups").thenReturn(response)

    async def run() -> list[UserGroup]:
        return await service.list_user_groups()

    groups = asyncio.run(run())
    assert len(groups) == 1


def test_async_list_application_users() -> None:
    client = mock(httpx.AsyncClient)
    service = AsyncPolicyActivityReportService(client)
    response = _make_data_envelope(
        data=[{"firstName": "T", "lastName": "U", "username": "tu"}],
    )
    when(client).get(f"{_BASE_PATH}/share/application-users").thenReturn(response)

    async def run() -> list[ApplicationUser]:
        return await service.list_application_users()

    users = asyncio.run(run())
    assert len(users) == 1
    assert users[0].username == "tu"
