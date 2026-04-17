"""PDP E2E flows (JSON + XML + error).

Exercises :class:`PdpClient` / :class:`AsyncPdpClient` against a WireMock
container stubbed with PDP-shaped responses. The OpenAPI spec's PDP
examples are sparse (and never include the XML variant), so this module
registers its own stubs for ``/dpc/authorization/pdp`` alongside the
token stub that :func:`seeded_wiremock` provides.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from nextlabs_sdk.exceptions import NextLabsError
from nextlabs_sdk.pdp import (
    Action,
    Application,
    AsyncPdpClient,
    ContentType,
    Decision,
    EvalRequest,
    PdpClient,
    Resource,
    Subject,
)

_PDP_ENDPOINT = "/dpc/authorization/pdp"
_XACML_NS = "urn:oasis:names:tc:xacml:3.0:core:schema:wd-17"


def _json_permit_body() -> dict[str, object]:
    return {
        "Response": [
            {
                "Decision": "Permit",
                "Status": {
                    "StatusCode": {"Value": "urn:oasis:names:tc:xacml:1.0:status:ok"}
                },
            },
        ],
    }


def _xml_permit_body() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response xmlns="{_XACML_NS}">'
        "<Result>"
        "<Decision>Permit</Decision>"
        '<Status><StatusCode Value="urn:oasis:names:tc:xacml:1.0:status:ok"/></Status>'
        "</Result>"
        "</Response>"
    )


@pytest.fixture
def pdp_stubs(seeded_wiremock: str) -> str:
    """Register PDP response stubs on top of the seeded base URL."""
    json_mapping = {
        "priority": 1,
        "request": {
            "method": "POST",
            "urlPath": _PDP_ENDPOINT,
            "headers": {"Content-Type": {"contains": "application/json"}},
        },
        "response": {
            "status": 200,
            "headers": {"Content-Type": "application/json"},
            "jsonBody": _json_permit_body(),
        },
    }
    xml_mapping = {
        "priority": 1,
        "request": {
            "method": "POST",
            "urlPath": _PDP_ENDPOINT,
            "headers": {"Content-Type": {"contains": "application/xml"}},
        },
        "response": {
            "status": 200,
            "headers": {"Content-Type": "application/xml"},
            "body": _xml_permit_body(),
        },
    }
    with httpx.Client(timeout=5.0) as http:
        http.post(f"{seeded_wiremock}/__admin/mappings", json=json_mapping)
        http.post(f"{seeded_wiremock}/__admin/mappings", json=xml_mapping)
    return seeded_wiremock


@pytest.fixture
def pdp_error_stub(seeded_wiremock: str) -> str:
    """Replace the PDP endpoint with a 400 responder."""
    mapping = {
        "priority": 1,
        "request": {"method": "POST", "urlPath": _PDP_ENDPOINT},
        "response": {"status": 400, "body": "bad request"},
    }
    httpx.post(
        f"{seeded_wiremock}/__admin/mappings",
        json=mapping,
        timeout=5.0,
    )
    return seeded_wiremock


def _sample_request() -> EvalRequest:
    return EvalRequest(
        subject=Subject(id="alice"),
        resource=Resource(id="doc:1", type="document"),
        action=Action(id="read"),
        application=Application(id="app-1"),
    )


def test_sync_pdp_evaluate_json(
    pdp_client: PdpClient,
    pdp_stubs: str,
) -> None:
    assert pdp_stubs
    response = pdp_client.evaluate(_sample_request())
    assert response.eval_results
    assert response.eval_results[0].decision is Decision.PERMIT


def test_sync_pdp_evaluate_xml(
    pdp_client: PdpClient,
    pdp_stubs: str,
) -> None:
    assert pdp_stubs
    response = pdp_client.evaluate(_sample_request(), content_type=ContentType.XML)
    assert response.eval_results
    assert response.eval_results[0].decision is Decision.PERMIT


def test_sync_pdp_bad_request_raises(
    pdp_client: PdpClient,
    pdp_error_stub: str,
) -> None:
    assert pdp_error_stub
    with pytest.raises(NextLabsError):
        pdp_client.evaluate(_sample_request())


def test_async_pdp_evaluate_json(
    seeded_wiremock: str,
    pdp_stubs: str,
) -> None:
    assert pdp_stubs

    async def _run() -> object:
        client = AsyncPdpClient(
            base_url=seeded_wiremock,
            client_id="e2e-client",
            client_secret="e2e-secret",
        )
        try:
            return await client.evaluate(_sample_request())
        finally:
            await client.close()

    response = asyncio.run(_run())
    eval_results = getattr(response, "eval_results", [])
    assert eval_results
    assert eval_results[0].decision is Decision.PERMIT
