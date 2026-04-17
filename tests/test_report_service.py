from __future__ import annotations

import httpx
from mockito import mock, when
import pytest

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
from nextlabs_sdk._cloudaz._reports import PolicyActivityReportService
from nextlabs_sdk._pagination import SyncPaginator
from nextlabs_sdk.exceptions import ServerError

BASE_URL = "https://cloudaz.example.com"
_BASE_PATH = "/nextlabs-reporter/api/v1/policy-activity-reports"


def _enforce_params(page: int = 0) -> dict[str, object]:
    return {
        "page": page,
        "size": 20,
        "sortBy": "rowId",
        "sortOrder": "ascending",
    }


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


def _list_params(
    *,
    title: str = "",
    is_shared: bool = True,
    policy_decision: str = "AD",
    sort_order: str = "ascending",
    size: int = 20,
    page: int = 0,
) -> dict[str, object]:
    return {
        "title": title,
        "isShared": is_shared,
        "policyDecision": policy_decision,
        "sortBy": "title",
        "sortOrder": sort_order,
        "size": size,
        "page": page,
    }


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


@pytest.fixture
def client():
    return mock(httpx.Client)


@pytest.fixture
def service(client):
    return PolicyActivityReportService(client)


# --- list ---


def test_list_returns_paginator(client, service):
    when(client).get(_BASE_PATH, params=_list_params()).thenReturn(
        _make_reporter_envelope(content=[_make_report_summary()]),
    )

    paginator = service.list()

    assert isinstance(paginator, SyncPaginator)
    reports = list(paginator)
    assert len(reports) == 1
    assert isinstance(reports[0], PolicyActivityReport)
    assert reports[0].id == 8


def test_list_paginates_multiple_pages(client, service):
    r1 = _make_report_summary()
    r1["id"] = 1
    r2 = _make_report_summary()
    r2["id"] = 2
    page0 = _make_reporter_envelope(content=[r1], total_pages=2, total_elements=2)
    page1 = _make_reporter_envelope(content=[r2], total_pages=2, total_elements=2)

    when(client).get(_BASE_PATH, params=_list_params(page=0)).thenReturn(page0)
    when(client).get(_BASE_PATH, params=_list_params(page=1)).thenReturn(page1)

    reports = list(service.list())
    assert len(reports) == 2
    assert reports[0].id == 1
    assert reports[1].id == 2


def test_list_with_filters(client, service):
    params = _list_params(
        title="Deny",
        is_shared=False,
        policy_decision="D",
        sort_order="descending",
        size=10,
    )
    when(client).get(_BASE_PATH, params=params).thenReturn(
        _make_reporter_envelope(content=[], total_elements=0),
    )

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


def test_get_returns_detail(client, service):
    when(client).get(f"{_BASE_PATH}/42").thenReturn(
        _make_data_envelope(
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
        ),
    )

    detail = service.get(42)

    assert isinstance(detail, PolicyActivityReportDetail)
    assert detail.criteria.filters is not None
    assert detail.criteria.filters.general is not None
    assert detail.criteria.filters.general.type == "custom"
    assert len(detail.widgets) == 1


# --- create / modify (same-shape, HTTP verb differs) ---


def _stub_report_call(client, verb: str, url: str, payload: dict[str, object]):
    response = _make_data_envelope(data=_make_report_summary())
    stub = when(client)
    if verb == "post":
        stub.post(url, json=payload).thenReturn(response)
    else:
        stub.put(url, json=payload).thenReturn(response)


@pytest.mark.parametrize(
    "verb,url,invoke",
    [
        pytest.param(
            "post",
            _BASE_PATH,
            lambda s, r: s.create(r),
            id="create",
        ),
        pytest.param(
            "put",
            f"{_BASE_PATH}/42",
            lambda s, r: s.modify(42, r),
            id="modify",
        ),
    ],
)
def test_create_and_modify_return_summary(client, service, verb, url, invoke):
    request = _make_simple_request()
    payload = request.model_dump(by_alias=True, exclude_none=True)
    _stub_report_call(client, verb, url, payload)

    report = invoke(service, request)

    assert isinstance(report, PolicyActivityReport)
    assert report.id == 8


# --- delete ---


@pytest.mark.parametrize(
    "status,json_body,expectation",
    [
        pytest.param(
            200,
            {"statusCode": "1002", "message": "Data deleted successfully"},
            None,
            id="success",
        ),
        pytest.param(500, {"message": "Server error"}, ServerError, id="server-error"),
    ],
)
def test_delete_dispatches_to_api(client, service, status, json_body, expectation):
    request = DeleteReportsRequest(report_ids=[5, 10] if expectation is None else [999])
    when(client).post(
        f"{_BASE_PATH}/delete",
        json={"reportIds": request.report_ids},
    ).thenReturn(httpx.Response(status, json=json_body, request=_make_request()))

    if expectation is None:
        service.delete(request)
    else:
        with pytest.raises(expectation):
            service.delete(request)


# --- get_widgets ---


def test_get_widgets_returns_widget_data(client, service):
    when(client).get(f"{_BASE_PATH}/42/widgets").thenReturn(
        _make_data_envelope(
            data={
                "enforcements": [
                    {
                        "hour": 1708070400000,
                        "allowCount": 5,
                        "denyCount": 2,
                        "decisionCount": 7,
                    },
                ],
            },
        ),
    )

    data = service.get_widgets(42)

    assert isinstance(data, WidgetData)
    assert len(data.enforcements) == 1
    assert data.enforcements[0].allow_count == 5


# --- get_enforcements ---


def test_get_enforcements_returns_paginator(client, service):
    when(client).get(
        f"{_BASE_PATH}/42/enforcements",
        params=_enforce_params(),
    ).thenReturn(_make_reporter_envelope(content=[_make_enforcement_data()]))

    paginator = service.get_enforcements(42)

    assert isinstance(paginator, SyncPaginator)
    entries = list(paginator)
    assert len(entries) == 1
    assert isinstance(entries[0], EnforcementEntry)
    assert entries[0].row_id == 2


def test_get_enforcements_multi_page(client, service):
    e1 = _make_enforcement_data()
    e1["ROW_ID"] = 1
    e2 = _make_enforcement_data()
    e2["ROW_ID"] = 2
    page0 = _make_reporter_envelope(content=[e1], total_pages=2, total_elements=2)
    page1 = _make_reporter_envelope(content=[e2], total_pages=2, total_elements=2)

    when(client).get(
        f"{_BASE_PATH}/42/enforcements",
        params=_enforce_params(0),
    ).thenReturn(page0)
    when(client).get(
        f"{_BASE_PATH}/42/enforcements",
        params=_enforce_params(1),
    ).thenReturn(page1)

    entries = list(service.get_enforcements(42))
    assert len(entries) == 2
    assert entries[0].row_id == 1
    assert entries[1].row_id == 2


# --- export ---


@pytest.mark.parametrize(
    "status,content,expectation,expected_result",
    [
        pytest.param(
            200,
            b"ROW_ID,TIME,USER_NAME\n1,2024-01-01,user\n",
            None,
            b"ROW_ID,TIME,USER_NAME\n1,2024-01-01,user\n",
            id="success",
        ),
        pytest.param(500, None, ServerError, None, id="server-error"),
    ],
)
def test_export(client, service, status, content, expectation, expected_result):
    response = (
        httpx.Response(500, json={"message": "error"}, request=_make_request())
        if status == 500
        else httpx.Response(200, content=content, request=_make_request())
    )
    when(client).post(
        f"{_BASE_PATH}/42/export",
        params={"sortBy": "rowId", "sortOrder": "ascending"},
    ).thenReturn(response)

    if expectation is None:
        assert service.export(42) == expected_result
    else:
        with pytest.raises(expectation):
            service.export(42)


# --- generate_widgets ---


def test_generate_widgets_returns_widget_data(client, service):
    request = _make_simple_request()
    when(client).post(
        f"{_BASE_PATH}/generate/widgets",
        json=request.model_dump(by_alias=True, exclude_none=True),
    ).thenReturn(
        _make_data_envelope(
            data={
                "enforcements": [
                    {"hour": 100, "allowCount": 1, "denyCount": 0, "decisionCount": 1}
                ]
            },
        ),
    )

    data = service.generate_widgets(request)

    assert isinstance(data, WidgetData)
    assert data.enforcements[0].allow_count == 1


# --- generate_enforcements ---


def test_generate_enforcements_returns_paginator(client, service):
    request = _make_simple_request()
    payload = request.model_dump(by_alias=True, exclude_none=True)
    when(client).post(
        f"{_BASE_PATH}/generate/enforcements",
        json=payload,
        params=_enforce_params(),
    ).thenReturn(_make_reporter_envelope(content=[_make_enforcement_data()]))

    entries = list(service.generate_enforcements(request))

    assert len(entries) == 1
    assert entries[0].row_id == 2


# --- generate_export ---


def test_generate_export_returns_bytes(client, service):
    request = _make_simple_request()
    payload = request.model_dump(by_alias=True, exclude_none=True)
    when(client).post(
        f"{_BASE_PATH}/generate/export",
        json=payload,
        params={"sortBy": "rowId", "sortOrder": "ascending"},
    ).thenReturn(httpx.Response(200, content=b"data", request=_make_request()))

    assert service.generate_export(request) == b"data"


# --- Cached data ---


def test_list_cached_users(client, service):
    when(client).get(f"{_BASE_PATH}/users").thenReturn(
        _make_data_envelope(
            data=[
                {
                    "displayName": "LocalSystem@localhost",
                    "firstName": "User",
                    "lastName": "System",
                }
            ],
        ),
    )

    users = service.list_cached_users()

    assert len(users) == 1
    assert isinstance(users[0], CachedUser)
    assert users[0].display_name == "LocalSystem@localhost"


def test_list_cached_policies(client, service):
    when(client).get(f"{_BASE_PATH}/policies").thenReturn(
        _make_data_envelope(
            data=[{"name": "Test", "fullName": "/ROOT_187/Testing Policy"}],
        ),
    )

    policies = service.list_cached_policies()

    assert len(policies) == 1
    assert isinstance(policies[0], CachedPolicy)
    assert policies[0].full_name == "/ROOT_187/Testing Policy"


def test_get_resource_actions(client, service):
    when(client).get(f"{_BASE_PATH}/resource-actions").thenReturn(
        _make_data_envelope(
            data={
                "policyModelActions": {
                    "test type": [
                        {"policyModelId": 43, "label": "action1", "shortCode": "dw"}
                    ],
                },
            },
        ),
    )

    result = service.get_resource_actions()

    assert isinstance(result, ResourceActions)
    assert "test type" in result.policy_model_actions


def test_get_mappings(client, service):
    when(client).get(f"{_BASE_PATH}/mappings").thenReturn(
        _make_data_envelope(
            data={
                "resource": [
                    {
                        "id": 11,
                        "name": "FROM_RESOURCE_NAME",
                        "mappedColumn": "FROM_RESOURCE_NAME",
                        "dataType": "STRING",
                        "attrType": "RESOURCE",
                        "isDynamic": False,
                    }
                ],
                "user": [
                    {
                        "id": 2,
                        "name": "USER_NAME",
                        "mappedColumn": "USER_NAME",
                        "dataType": "STRING",
                        "attrType": "USER",
                        "isDynamic": False,
                    }
                ],
                "others": [
                    {
                        "id": 1,
                        "name": "DATE",
                        "mappedColumn": "TIME",
                        "dataType": "TIMESTAMP",
                        "attrType": "OTHERS",
                        "isDynamic": False,
                    }
                ],
            },
        ),
    )

    result = service.get_mappings()

    assert isinstance(result, AttributeMappings)
    assert len(result.resource) == 1
    assert len(result.user) == 1


# --- Sharing ---


def test_list_user_groups(client, service):
    when(client).get(f"{_BASE_PATH}/share/user-groups").thenReturn(
        _make_data_envelope(data=[{"title": "All Policy Server Users", "id": 1}]),
    )

    groups = service.list_user_groups()

    assert len(groups) == 1
    assert isinstance(groups[0], UserGroup)
    assert groups[0].title == "All Policy Server Users"


def test_list_application_users(client, service):
    when(client).get(f"{_BASE_PATH}/share/application-users").thenReturn(
        _make_data_envelope(
            data=[{"firstName": "Test", "lastName": "User", "username": "testuser"}],
        ),
    )

    users = service.list_application_users()

    assert len(users) == 1
    assert isinstance(users[0], ApplicationUser)
    assert users[0].username == "testuser"
