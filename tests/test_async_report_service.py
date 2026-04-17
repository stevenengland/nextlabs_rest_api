from __future__ import annotations

import asyncio
from typing import Any, Coroutine, TypeVar

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

T = TypeVar("T")

BASE_URL = "https://cloudaz.example.com"
_BASE_PATH = "/nextlabs-reporter/api/v1/policy-activity-reports"


def _list_params(page: int = 0) -> dict[str, Any]:
    return {
        "title": "",
        "isShared": True,
        "policyDecision": "AD",
        "sortBy": "title",
        "sortOrder": "ascending",
        "size": 20,
        "page": page,
    }


def _enforcement_params() -> dict[str, Any]:
    return {"page": 0, "size": 20, "sortBy": "rowId", "sortOrder": "ascending"}


def _export_params() -> dict[str, str]:
    return {"sortBy": "rowId", "sortOrder": "ascending"}


def _run_async(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("POST", f"{BASE_URL}{path}")


def _make_envelope(
    data: Any = None,
    *,
    content=None,
    total_pages: int = 1,
    total_elements: int = 1,
) -> httpx.Response:
    if content is None:
        body = {
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": data,
        }
    else:
        body = {
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": {
                "content": content,
                "totalPages": total_pages,
                "totalElements": total_elements,
            },
        }
    return httpx.Response(200, json=body, request=_make_request())


def _make_report_summary(report_id: int = 8) -> dict[str, Any]:
    return {
        "id": report_id,
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


def _make_enforcement_data() -> dict[str, Any]:
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


@pytest.fixture
def service_client():
    client = mock(httpx.AsyncClient)
    return AsyncPolicyActivityReportService(client), client


def test_async_list_returns_paginator(service_client):
    service, client = service_client
    when(client).get(_BASE_PATH, params=_list_params()).thenReturn(
        _make_envelope(content=[_make_report_summary()]),
    )

    paginator = service.list()
    assert isinstance(paginator, AsyncPaginator)

    async def collect() -> list[PolicyActivityReport]:
        return [r async for r in paginator]

    reports = _run_async(collect())
    assert len(reports) == 1
    assert reports[0].id == 8


def test_async_list_multi_page(service_client):
    service, client = service_client
    when(client).get(_BASE_PATH, params=_list_params()).thenReturn(
        _make_envelope(
            content=[_make_report_summary(1)],
            total_pages=2,
            total_elements=2,
        ),
    )
    when(client).get(_BASE_PATH, params=_list_params(page=1)).thenReturn(
        _make_envelope(
            content=[_make_report_summary(2)],
            total_pages=2,
            total_elements=2,
        ),
    )

    async def collect() -> list[PolicyActivityReport]:
        return [r async for r in service.list()]

    reports = _run_async(collect())
    assert [r.id for r in reports] == [1, 2]


def test_async_get_returns_detail(service_client):
    service, client = service_client
    when(client).get(f"{_BASE_PATH}/42").thenReturn(
        _make_envelope(
            data={
                "criteria": {
                    "filters": {"general": {"type": "custom"}},
                    "pagesize": 20,
                },
                "widgets": [
                    {
                        "id": 1,
                        "name": "e",
                        "title": "T",
                        "chartType": "line",
                        "attributeName": "d",
                        "maxSize": 10,
                    },
                ],
            },
        ),
    )

    detail: PolicyActivityReportDetail = _run_async(service.get(42))
    assert detail.criteria.filters is not None
    assert detail.criteria.filters.general is not None
    assert detail.criteria.filters.general.type == "custom"


@pytest.mark.parametrize(
    "method_name,http_verb,path",
    [
        pytest.param("create", "post", _BASE_PATH, id="create"),
        pytest.param("modify", "put", f"{_BASE_PATH}/42", id="modify"),
    ],
)
def test_async_create_or_modify_returns_summary(
    service_client, method_name, http_verb, path
):
    service, client = service_client
    request = _make_simple_request()
    payload = request.model_dump(by_alias=True, exclude_none=True)
    getattr(when(client), http_verb)(path, json=payload).thenReturn(
        _make_envelope(data=_make_report_summary()),
    )

    if method_name == "create":
        report: PolicyActivityReport = _run_async(service.create(request))
    else:
        report = _run_async(service.modify(42, request))
    assert report.id == 8


def test_async_delete_by_ids(service_client):
    service, client = service_client
    request = DeleteReportsRequest(report_ids=[5, 10])
    when(client).post(f"{_BASE_PATH}/delete", json={"reportIds": [5, 10]}).thenReturn(
        httpx.Response(
            200,
            json={"statusCode": "1002", "message": "ok"},
            request=_make_request(),
        ),
    )

    _run_async(service.delete(request))


def test_async_delete_raises_on_error(service_client):
    service, client = service_client
    request = DeleteReportsRequest(report_ids=[999])
    when(client).post(f"{_BASE_PATH}/delete", json={"reportIds": [999]}).thenReturn(
        httpx.Response(500, json={"message": "error"}, request=_make_request()),
    )

    with pytest.raises(ServerError):
        _run_async(service.delete(request))


def test_async_get_widgets(service_client):
    service, client = service_client
    when(client).get(f"{_BASE_PATH}/42/widgets").thenReturn(
        _make_envelope(
            data={
                "enforcements": [
                    {"hour": 100, "allowCount": 1, "denyCount": 0, "decisionCount": 1},
                ],
            },
        ),
    )

    data: WidgetData = _run_async(service.get_widgets(42))
    assert len(data.enforcements) == 1


def test_async_get_enforcements(service_client):
    service, client = service_client
    when(client).get(
        f"{_BASE_PATH}/42/enforcements",
        params=_enforcement_params(),
    ).thenReturn(_make_envelope(content=[_make_enforcement_data()]))

    async def collect() -> list[EnforcementEntry]:
        return [e async for e in service.get_enforcements(42)]

    entries = _run_async(collect())
    assert len(entries) == 1
    assert entries[0].row_id == 2


def test_async_export_returns_bytes(service_client):
    service, client = service_client
    csv = b"data"
    when(client).post(
        f"{_BASE_PATH}/42/export",
        params=_export_params(),
    ).thenReturn(httpx.Response(200, content=csv, request=_make_request()))

    assert _run_async(service.export(42)) == csv


def test_async_generate_widgets(service_client):
    service, client = service_client
    request = _make_simple_request()
    when(client).post(
        f"{_BASE_PATH}/generate/widgets",
        json=request.model_dump(by_alias=True, exclude_none=True),
    ).thenReturn(
        _make_envelope(
            data={
                "enforcements": [
                    {"hour": 100, "allowCount": 0, "denyCount": 0, "decisionCount": 0},
                ],
            },
        ),
    )

    data: WidgetData = _run_async(service.generate_widgets(request))
    assert len(data.enforcements) == 1


def test_async_generate_enforcements(service_client):
    service, client = service_client
    request = _make_simple_request()
    payload = request.model_dump(by_alias=True, exclude_none=True)
    when(client).post(
        f"{_BASE_PATH}/generate/enforcements",
        json=payload,
        params=_enforcement_params(),
    ).thenReturn(_make_envelope(content=[_make_enforcement_data()]))

    async def collect() -> list[EnforcementEntry]:
        return [e async for e in service.generate_enforcements(request)]

    assert len(_run_async(collect())) == 1


def test_async_generate_export(service_client):
    service, client = service_client
    request = _make_simple_request()
    payload = request.model_dump(by_alias=True, exclude_none=True)
    csv = b"exported"
    when(client).post(
        f"{_BASE_PATH}/generate/export",
        json=payload,
        params=_export_params(),
    ).thenReturn(httpx.Response(200, content=csv, request=_make_request()))

    assert _run_async(service.generate_export(request)) == csv


def test_async_list_cached_users(service_client):
    service, client = service_client
    when(client).get(f"{_BASE_PATH}/users").thenReturn(
        _make_envelope(
            data=[{"displayName": "test@localhost", "firstName": "T", "lastName": "U"}],
        ),
    )

    users: list[CachedUser] = _run_async(service.list_cached_users())
    assert len(users) == 1


def test_async_list_cached_policies(service_client):
    service, client = service_client
    when(client).get(f"{_BASE_PATH}/policies").thenReturn(
        _make_envelope(data=[{"name": "P", "fullName": "/ROOT/P"}]),
    )

    policies: list[CachedPolicy] = _run_async(service.list_cached_policies())
    assert len(policies) == 1


def test_async_get_resource_actions(service_client):
    service, client = service_client
    when(client).get(f"{_BASE_PATH}/resource-actions").thenReturn(
        _make_envelope(
            data={
                "policyModelActions": {
                    "t": [{"policyModelId": 1, "label": "a", "shortCode": "x"}],
                },
            },
        ),
    )

    result: ResourceActions = _run_async(service.get_resource_actions())
    assert "t" in result.policy_model_actions


def test_async_get_mappings(service_client):
    service, client = service_client

    def _mapping(id_: int, name: str, attr_type: str) -> dict[str, Any]:
        return {
            "id": id_,
            "name": name,
            "mappedColumn": name,
            "dataType": "STRING",
            "attrType": attr_type,
            "isDynamic": False,
        }

    when(client).get(f"{_BASE_PATH}/mappings").thenReturn(
        _make_envelope(
            data={
                "resource": [_mapping(1, "N", "RESOURCE")],
                "user": [_mapping(2, "U", "USER")],
                "others": [_mapping(3, "O", "OTHERS")],
            },
        ),
    )

    result: AttributeMappings = _run_async(service.get_mappings())
    assert len(result.resource) == 1


def test_async_list_user_groups(service_client):
    service, client = service_client
    when(client).get(f"{_BASE_PATH}/share/user-groups").thenReturn(
        _make_envelope(data=[{"title": "Group", "id": 1}]),
    )

    groups: list[UserGroup] = _run_async(service.list_user_groups())
    assert len(groups) == 1


def test_async_list_application_users(service_client):
    service, client = service_client
    when(client).get(f"{_BASE_PATH}/share/application-users").thenReturn(
        _make_envelope(data=[{"firstName": "T", "lastName": "U", "username": "tu"}]),
    )

    users: list[ApplicationUser] = _run_async(service.list_application_users())
    assert len(users) == 1
    assert users[0].username == "tu"
