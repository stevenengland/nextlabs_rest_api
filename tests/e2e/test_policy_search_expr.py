"""E2E round trip for the ``--where`` transpiler across match types.

Drives ``nextlabs policies search --where`` against a WireMock backend and
inspects the recorded request body, pinning the ``SINGLE`` /
``SINGLE_EXACT_MATCH`` operator boundary and the ``DATE`` epoch-millisecond
window alongside the nested-attribute and list semantics.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from typing import Any

import httpx

POLICY_SEARCH_PATH = "/console/api/v1/policy/search"
_STUB_PRIORITY = 1

# 2024-01-01T00:00:00Z and 2024-02-01T00:00:00Z in epoch milliseconds.
_FROM_DATE_MS = 1704067200000
_TO_DATE_MS = 1706745600000


def _policy_entry() -> dict[str, Any]:
    return {
        "id": 1,
        "name": "Allow helpdesk",
        "status": "DRAFT",
        "effectType": "ALLOW",
        "lastUpdatedDate": _TO_DATE_MS,
        "createdDate": _FROM_DATE_MS,
    }


def _search_envelope() -> dict[str, Any]:
    return {
        "statusCode": "1000",
        "message": "OK",
        "data": [_policy_entry()],
        "pageNo": 0,
        "pageSize": 20,
        "totalPages": 1,
        "totalNoOfRecords": 1,
    }


def _register_search_stub(base_url: str) -> None:
    response = httpx.post(
        f"{base_url}/__admin/mappings",
        json={
            "priority": _STUB_PRIORITY,
            "request": {"method": "POST", "urlPath": POLICY_SEARCH_PATH},
            "response": {
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "jsonBody": _search_envelope(),
            },
        },
        timeout=5.0,
    )
    response.raise_for_status()


def _captured_search_body(base_url: str) -> dict[str, Any]:
    journal = httpx.get(f"{base_url}/__admin/requests", timeout=5.0).json()
    for entry in journal["requests"]:
        request = entry["request"]
        if request["method"] == "POST" and request["url"] == POLICY_SEARCH_PATH:
            return json.loads(request["body"])
    raise AssertionError("no policy search request was recorded")


def test_where_round_trips_every_match_type(
    seeded_wiremock: str,
    cli_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    # given a stubbed policy-search backend and a multi-criteria filter
    _register_search_stub(seeded_wiremock)
    where = (
        'name sw "Allow" '
        'and effectType co "ALLOW" '
        'and (status eq "DRAFT" or status eq "APPROVED") '
        'and tags[key eq "helpdesk"] '
        'and text co "ticket" '
        'and lastUpdatedDate ge "2024-01-01" '
        'and lastUpdatedDate le "2024-02-01"'
    )

    # when the CLI runs the search end to end
    result = cli_runner("policies", "search", "--where", where)

    # then the command succeeds and the request body round-trips every shape
    assert result.returncode == 0, result.stderr
    fields = {
        field["field"]: field
        for field in _captured_search_body(seeded_wiremock)["criteria"]["fields"]
    }

    assert fields["name"]["type"] == "SINGLE"
    assert fields["name"]["value"] == {"type": "String", "value": "Allow"}

    assert fields["effectType"]["type"] == "SINGLE_EXACT_MATCH"
    assert fields["effectType"]["value"] == {"type": "String", "value": "ALLOW"}

    assert fields["status"]["type"] == "MULTI_EXACT_MATCH"
    assert fields["status"]["value"] == {
        "type": "String",
        "value": ["DRAFT", "APPROVED"],
    }

    assert fields["tags"]["type"] == "NESTED"
    assert fields["tags"]["nestedField"] == "tags.key"
    assert fields["tags"]["value"] == {"type": "String", "value": "helpdesk"}

    assert fields["text"]["type"] == "TEXT"
    assert fields["text"]["value"] == {
        "type": "Text",
        "fields": ["name", "description"],
        "value": "ticket",
    }

    assert fields["lastUpdatedDate"]["type"] == "DATE"
    assert fields["lastUpdatedDate"]["value"] == {
        "type": "Date",
        "fromDate": _FROM_DATE_MS,
        "toDate": _TO_DATE_MS,
    }
