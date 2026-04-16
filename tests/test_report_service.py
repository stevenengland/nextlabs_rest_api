from __future__ import annotations

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._report_models import (
    DeleteReportsRequest,
    PolicyActivityReport,
    PolicyActivityReportDetail,
    PolicyActivityReportRequest,
    ReportCriteria,
    ReportFilterGeneral,
    ReportFilters,
    ReportWidget,
)
from nextlabs_sdk._cloudaz._reports import PolicyActivityReportService
from nextlabs_sdk._pagination import SyncPaginator
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


# --- list ---


def test_list_returns_paginator() -> None:
    client = mock(httpx.Client)
    service = PolicyActivityReportService(client)
    response = _make_reporter_envelope(
        content=[_make_report_summary()],
        total_pages=1,
        total_elements=1,
    )
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

    assert isinstance(paginator, SyncPaginator)
    reports = list(paginator)
    assert len(reports) == 1
    assert isinstance(reports[0], PolicyActivityReport)
    assert reports[0].id == 8


def test_list_paginates_multiple_pages() -> None:
    client = mock(httpx.Client)
    service = PolicyActivityReportService(client)
    r1 = _make_report_summary()
    r1["id"] = 1
    r2 = _make_report_summary()
    r2["id"] = 2

    page0 = _make_reporter_envelope(content=[r1], total_pages=2, total_elements=2)
    page1 = _make_reporter_envelope(content=[r2], total_pages=2, total_elements=2)

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
    ).thenReturn(page0)
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
    ).thenReturn(page1)

    reports = list(service.list())
    assert len(reports) == 2
    assert reports[0].id == 1
    assert reports[1].id == 2


def test_list_with_filters() -> None:
    client = mock(httpx.Client)
    service = PolicyActivityReportService(client)
    response = _make_reporter_envelope(content=[], total_elements=0)
    when(client).get(
        _BASE_PATH,
        params={
            "title": "Deny",
            "isShared": False,
            "policyDecision": "D",
            "sortBy": "title",
            "sortOrder": "descending",
            "size": 10,
            "page": 0,
        },
    ).thenReturn(response)

    reports = list(
        service.list(
            title="Deny",
            is_shared=False,
            policy_decision="D",
            sort_order="descending",
            page_size=10,
        )
    )
    assert reports == []


# --- get ---


def test_get_returns_detail() -> None:
    client = mock(httpx.Client)
    service = PolicyActivityReportService(client)
    response = _make_data_envelope(
        data={
            "criteria": {
                "filters": {"general": {"type": "custom"}},
                "header": ["USER_NAME"],
                "pagesize": 20,
            },
            "widgets": [
                {
                    "id": 1,
                    "name": "enforcement",
                    "title": "Trend",
                    "chartType": "line",
                    "attributeName": "decision",
                    "maxSize": 10,
                },
            ],
        },
    )
    when(client).get(f"{_BASE_PATH}/42").thenReturn(response)

    detail = service.get(42)

    assert isinstance(detail, PolicyActivityReportDetail)
    assert detail.criteria.filters is not None
    assert detail.criteria.filters.general is not None
    assert detail.criteria.filters.general.type == "custom"
    assert len(detail.widgets) == 1


# --- create ---


def test_create_returns_summary() -> None:
    client = mock(httpx.Client)
    service = PolicyActivityReportService(client)
    request = _make_simple_request()
    response = _make_data_envelope(data=_make_report_summary())
    when(client).post(
        _BASE_PATH,
        json=request.model_dump(by_alias=True, exclude_none=True),
    ).thenReturn(response)

    report = service.create(request)

    assert isinstance(report, PolicyActivityReport)
    assert report.id == 8


# --- modify ---


def test_modify_returns_summary() -> None:
    client = mock(httpx.Client)
    service = PolicyActivityReportService(client)
    request = _make_simple_request()
    response = _make_data_envelope(data=_make_report_summary())
    when(client).put(
        f"{_BASE_PATH}/42",
        json=request.model_dump(by_alias=True, exclude_none=True),
    ).thenReturn(response)

    report = service.modify(42, request)

    assert isinstance(report, PolicyActivityReport)
    assert report.id == 8


# --- delete ---


def test_delete_by_ids() -> None:
    client = mock(httpx.Client)
    service = PolicyActivityReportService(client)
    request = DeleteReportsRequest(report_ids=[5, 10])
    response = httpx.Response(
        200,
        json={"statusCode": "1002", "message": "Data deleted successfully"},
        request=_make_request(),
    )
    when(client).post(
        f"{_BASE_PATH}/delete",
        json={"reportIds": [5, 10]},
    ).thenReturn(response)

    service.delete(request)


def test_delete_raises_on_error() -> None:
    client = mock(httpx.Client)
    service = PolicyActivityReportService(client)
    request = DeleteReportsRequest(report_ids=[999])
    response = httpx.Response(
        500,
        json={"message": "Server error"},
        request=_make_request(),
    )
    when(client).post(
        f"{_BASE_PATH}/delete",
        json={"reportIds": [999]},
    ).thenReturn(response)

    with pytest.raises(ServerError):
        service.delete(request)
