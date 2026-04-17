"""Unit test for the stub-mapping builder."""

from __future__ import annotations

from tests._openapi.examples import ExampleCase
from tests.e2e._stubs import build_mapping


def test_build_mapping_from_simple_case() -> None:
    case = ExampleCase(
        path="/console/api/v1/component/mgmt/active/{id}",
        method="get",
        status="200",
        content_type="application/json",
        body='{"statusCode": "1003", "message": "ok", "data": null}',
    )
    mapping = build_mapping(case)
    assert mapping["request"]["method"] == "GET"
    assert mapping["request"]["urlPathPattern"] == (
        "/console/api/v1/component/mgmt/active/[^/]+"
    )
    assert mapping["response"]["status"] == 200
    assert mapping["response"]["headers"]["Content-Type"] == "application/json"
    assert '"statusCode"' in mapping["response"]["body"]
