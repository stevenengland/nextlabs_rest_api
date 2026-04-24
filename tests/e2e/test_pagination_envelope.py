"""Verify pagination envelope + zero-indexed ``pageNo`` assumption holds
across every CloudAz endpoint family the SDK paginates.

Covers the four families called out in issue #99:

* tag listing (``/console/api/v1/config/tags/list/{type}``)
* component saved searches (``/console/api/v1/component/search/savedlist``)
* reporter audit logs (``/nextlabs-reporter/api/v1/auditLogs/search``)
* policy activity reports (``/nextlabs-reporter/api/v1/policy-activity-reports``)

Each test seeds WireMock with three per-page mappings (higher priority than
the OpenAPI-example fallback stub) and walks the SDK paginator to the end.
It then asserts the total record count matches what the envelope reports,
the paginator stops at ``total_pages - 1``, and WireMock was not asked for
a fourth page.
"""

from __future__ import annotations

from typing import Any

import httpx

from nextlabs_sdk.cloudaz import AuditLogQuery, CloudAzClient, TagType

TOTAL_PAGES = 3
PAGE_SIZE = 2
TOTAL_RECORDS = TOTAL_PAGES * PAGE_SIZE

# Higher priority (lower number) than the default OpenAPI-derived mappings so
# our per-page stubs win when the path matches.
_STUB_PRIORITY = 1
_FALLBACK_PRIORITY = 10


def _cloudaz_envelope(entries: list[dict[str, Any]], page_no: int) -> dict[str, Any]:
    return {
        "statusCode": "1000",
        "message": "OK",
        "data": entries,
        "pageNo": page_no,
        "pageSize": PAGE_SIZE,
        "totalPages": TOTAL_PAGES,
        "totalNoOfRecords": TOTAL_RECORDS,
    }


def _reporter_envelope(entries: list[dict[str, Any]], page_no: int) -> dict[str, Any]:
    return {
        "statusCode": "1000",
        "message": "OK",
        "data": {
            "content": entries,
            "number": page_no,
            "size": PAGE_SIZE,
            "totalPages": TOTAL_PAGES,
            "totalElements": TOTAL_RECORDS,
        },
    }


def _post_mapping(base_url: str, mapping: dict[str, Any]) -> None:
    response = httpx.post(f"{base_url}/__admin/mappings", json=mapping, timeout=5.0)
    response.raise_for_status()


def _register_fallback_404(base_url: str, url_pattern: str, method: str) -> None:
    """Catch-all stub that fails the test if the SDK walks past the last page."""
    _post_mapping(
        base_url,
        {
            "priority": _FALLBACK_PRIORITY,
            "request": {"method": method, "urlPathPattern": url_pattern},
            "response": {"status": 599, "body": "unexpected extra page request"},
        },
    )


def _register_get_pages(
    base_url: str,
    *,
    url_pattern: str,
    page_param: str,
    entry_factory: Any,
    envelope: Any,
) -> None:
    _register_fallback_404(base_url, url_pattern, "GET")
    for page_no in range(TOTAL_PAGES):
        entries = [entry_factory(page_no, index) for index in range(PAGE_SIZE)]
        _post_mapping(
            base_url,
            {
                "priority": _STUB_PRIORITY,
                "request": {
                    "method": "GET",
                    "urlPathPattern": url_pattern,
                    "queryParameters": {
                        page_param: {"equalTo": str(page_no)},
                    },
                },
                "response": {
                    "status": 200,
                    "headers": {"Content-Type": "application/json"},
                    "jsonBody": envelope(entries, page_no),
                },
            },
        )


def _register_post_body_pages(
    base_url: str,
    *,
    url_pattern: str,
    page_body_field: str,
    entry_factory: Any,
    envelope: Any,
) -> None:
    _register_fallback_404(base_url, url_pattern, "POST")
    for page_no in range(TOTAL_PAGES):
        entries = [entry_factory(page_no, index) for index in range(PAGE_SIZE)]
        _post_mapping(
            base_url,
            {
                "priority": _STUB_PRIORITY,
                "request": {
                    "method": "POST",
                    "urlPathPattern": url_pattern,
                    "bodyPatterns": [
                        {"matchesJsonPath": f"$.{page_body_field}"},
                        {
                            "matchesJsonPath": {
                                "expression": f"$.{page_body_field}",
                                "equalTo": str(page_no),
                            },
                        },
                    ],
                },
                "response": {
                    "status": 200,
                    "headers": {"Content-Type": "application/json"},
                    "jsonBody": envelope(entries, page_no),
                },
            },
        )


# ---------------------------------------------------------------------------
# Tag listing (/console/api/v1/config/tags/list/{type}) — CloudAz envelope
# ---------------------------------------------------------------------------


def _tag_entry(page_no: int, index: int) -> dict[str, Any]:
    row = page_no * PAGE_SIZE + index
    return {
        "id": 1000 + row,
        "key": f"tag-{row}",
        "label": f"Tag {row}",
        "type": TagType.COMPONENT.value,
        "status": "ACTIVE",
    }


def test_tag_listing_paginates_every_page_zero_indexed(
    wiremock_base_url: str,
    cloudaz_client: CloudAzClient,
) -> None:
    _register_get_pages(
        wiremock_base_url,
        url_pattern=r"/console/api/v1/config/tags/list/[^/]+",
        page_param="pageNo",
        entry_factory=_tag_entry,
        envelope=_cloudaz_envelope,
    )

    first = cloudaz_client.tags.list(
        TagType.COMPONENT,
        page_size=PAGE_SIZE,
    ).first_page()
    assert first.page_no == 0
    assert first.total_pages == TOTAL_PAGES
    assert first.total_records == TOTAL_RECORDS

    all_entries = list(
        cloudaz_client.tags.list(TagType.COMPONENT, page_size=PAGE_SIZE),
    )
    assert len(all_entries) == TOTAL_RECORDS
    assert [entry.key for entry in all_entries] == [
        f"tag-{row}" for row in range(TOTAL_RECORDS)
    ]


# ---------------------------------------------------------------------------
# Component saved searches — CloudAz envelope
# ---------------------------------------------------------------------------


def _saved_search_entry(page_no: int, index: int) -> dict[str, Any]:
    row = page_no * PAGE_SIZE + index
    return {
        "id": 2000 + row,
        "name": f"saved-{row}",
        "type": "COMPONENT",
    }


def test_saved_searches_paginates_every_page_zero_indexed(
    wiremock_base_url: str,
    cloudaz_client: CloudAzClient,
) -> None:
    _register_get_pages(
        wiremock_base_url,
        url_pattern=r"/console/api/v1/component/search/savedlist",
        page_param="pageNo",
        entry_factory=_saved_search_entry,
        envelope=_cloudaz_envelope,
    )

    entries = list(
        cloudaz_client.component_search.list_saved_searches(page_size=PAGE_SIZE),
    )

    assert len(entries) == TOTAL_RECORDS
    assert [entry.name for entry in entries] == [
        f"saved-{row}" for row in range(TOTAL_RECORDS)
    ]


# ---------------------------------------------------------------------------
# Reporter audit logs — reporter-paginated envelope, POST with pageNumber
# ---------------------------------------------------------------------------


def _audit_log_entry(page_no: int, index: int) -> dict[str, Any]:
    row = page_no * PAGE_SIZE + index
    return {
        "id": 3000 + row,
        "timestamp": 1_700_000_000 + row,
        "action": "CREATE",
        "actorId": 42,
        "actor": "alice",
        "entityType": "POLICY",
        "entityId": row,
    }


def test_reporter_audit_logs_paginates_every_page_zero_indexed(
    wiremock_base_url: str,
    cloudaz_client: CloudAzClient,
) -> None:
    _register_post_body_pages(
        wiremock_base_url,
        url_pattern=r"/nextlabs-reporter/api/v1/auditLogs/search",
        page_body_field="pageNumber",
        entry_factory=_audit_log_entry,
        envelope=_reporter_envelope,
    )

    query = AuditLogQuery(
        start_date=0,
        end_date=1_800_000_000,
        sort_by="timestamp",
        sort_order="DESC",
        page_size=PAGE_SIZE,
    )
    entries = list(cloudaz_client.audit_logs.search(query))

    assert len(entries) == TOTAL_RECORDS
    assert [entry.id for entry in entries] == [
        3000 + row for row in range(TOTAL_RECORDS)
    ]


# ---------------------------------------------------------------------------
# Policy activity reports — reporter-paginated envelope, GET with page= param
# ---------------------------------------------------------------------------


def _policy_report_entry(page_no: int, index: int) -> dict[str, Any]:
    row = page_no * PAGE_SIZE + index
    return {
        "id": 4000 + row,
        "title": f"report-{row}",
        "sharedMode": "PRIVATE",
        "decision": "AD",
        "dateMode": "RELATIVE",
        "windowMode": "LAST_7_DAYS",
        "startDate": "2025-01-01",
        "endDate": "2025-01-07",
        "lastUpdatedDate": "2025-01-07",
        "type": "POLICY_ACTIVITY",
    }


def test_policy_activity_reports_paginates_every_page_zero_indexed(
    wiremock_base_url: str,
    cloudaz_client: CloudAzClient,
) -> None:
    _register_get_pages(
        wiremock_base_url,
        url_pattern=r"/nextlabs-reporter/api/v1/policy-activity-reports",
        page_param="page",
        entry_factory=_policy_report_entry,
        envelope=_reporter_envelope,
    )

    entries = list(cloudaz_client.reports.list(page_size=PAGE_SIZE))

    assert len(entries) == TOTAL_RECORDS
    assert [entry.title for entry in entries] == [
        f"report-{row}" for row in range(TOTAL_RECORDS)
    ]
