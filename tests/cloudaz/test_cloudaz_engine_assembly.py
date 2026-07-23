from __future__ import annotations

import httpx
import pytest

from nextlabs_sdk._cloudaz._engine._assembly import assemble_page
from nextlabs_sdk._cloudaz._engine._dialect import (
    CLASSIC_ENVELOPE,
    PAGEABLE,
    REPORTER_ENVELOPE,
)
from nextlabs_sdk.cloudaz import ComponentLite
from nextlabs_sdk.exceptions import ApiError


def _request() -> httpx.Request:
    return httpx.Request("GET", "https://cloudaz.example.com/api")


def _component() -> dict[str, object]:
    return {
        "id": 101,
        "folderId": -1,
        "name": "Security Vulnerabilities",
        "fullName": "RESOURCE/Security Vulnerabilities",
        "status": "APPROVED",
        "modelId": 42,
        "modelType": "Support Tickets",
        "group": "RESOURCE",
        "lastUpdatedDate": 1713173211329,
        "createdDate": 1713171640267,
        "ownerId": 0,
        "ownerDisplayName": "Administrator",
        "modifiedById": 0,
        "modifiedBy": "Administrator",
        "hasIncludedIn": False,
        "hasSubComponents": False,
        "tags": [],
        "includedInComponents": [],
        "subComponents": [],
        "deploymentTime": 0,
        "deployed": True,
        "revisionCount": 1,
        "empty": False,
        "version": 2,
        "authorities": [],
        "preCreated": False,
        "referedInPolicies": False,
        "deploymentPending": False,
    }


def _classic(data: list[dict[str, object]], *, page_size: int | None) -> httpx.Response:
    body: dict[str, object] = {
        "statusCode": "1004",
        "message": "ok",
        "data": data,
        "totalPages": 1,
        "totalNoOfRecords": len(data),
    }
    if page_size is not None:
        body["pageSize"] = page_size
    return httpx.Response(200, json=body, request=_request())


def test_classic_envelope_honours_server_page_size():
    # given a classic envelope reporting pageSize=25
    response = _classic([_component()], page_size=25)
    # when assembled
    page = assemble_page(response, ComponentLite, 0, CLASSIC_ENVELOPE)
    # then page_size reflects the server value
    assert page.page_size == 25
    assert page.page_no == 0
    assert len(page.entries) == 1


def test_classic_envelope_falls_back_to_len_without_page_size():
    # given a classic envelope omitting pageSize
    response = _classic([_component()], page_size=None)
    # when assembled
    page = assemble_page(response, ComponentLite, 0, CLASSIC_ENVELOPE)
    # then page_size falls back to the length of the returned entries
    assert page.page_size == 1


@pytest.mark.parametrize(
    ("dialect", "response"),
    [
        (
            REPORTER_ENVELOPE,
            httpx.Response(
                200,
                json={
                    "statusCode": "1004",
                    "message": "ok",
                    "data": {
                        "content": [_component()],
                        "totalPages": 1,
                        "totalElements": 1,
                    },
                },
                request=_request(),
            ),
        ),
        (
            PAGEABLE,
            httpx.Response(
                200,
                json={
                    "content": [_component()],
                    "totalPages": 1,
                    "totalElements": 1,
                },
                request=_request(),
            ),
        ),
    ],
)
def test_reporter_and_pageable_use_len(dialect, response):
    # when assembled with a reporter or pageable dialect
    page = assemble_page(response, ComponentLite, 0, dialect)
    # then page_size is the length of the returned entries
    assert page.page_size == len(page.entries)


def test_no_data_envelope_yields_empty_page():
    # given a classic no-data envelope
    response = httpx.Response(
        200,
        json={
            "statusCode": "5000",
            "message": "No data found",
            "data": [],
        },
        request=_request(),
    )
    # when assembled
    page = assemble_page(response, ComponentLite, 0, CLASSIC_ENVELOPE)
    # then the page is empty, not an error
    assert page.entries == []
    assert page.total_pages == 0


def test_envelope_error_raises_api_error():
    # given a classic error envelope
    response = httpx.Response(
        200,
        json={"statusCode": "9001", "message": "boom"},
        request=_request(),
    )
    # then assembling raises ApiError
    with pytest.raises(ApiError):
        assemble_page(response, ComponentLite, 0, CLASSIC_ENVELOPE)


def test_malformed_entry_raises_api_error():
    # given a classic envelope whose entry fails model validation
    response = _classic([{"id": "not-an-int"}], page_size=1)
    # then assembling raises ApiError, not a raw pydantic ValidationError
    with pytest.raises(ApiError):
        assemble_page(response, ComponentLite, 0, CLASSIC_ENVELOPE)
