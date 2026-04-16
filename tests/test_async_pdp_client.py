from __future__ import annotations

import asyncio

import httpx
from mockito import mock, when, any as any_value, verify

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._pdp._async_client import AsyncPdpClient
from nextlabs_sdk._pdp._enums import ContentType, Decision
from nextlabs_sdk._pdp._request_models import (
    Action,
    Application,
    EvalRequest,
    PermissionsRequest,
    Resource,
    Subject,
)

BASE_URL = "https://pdp.example.com"
PDP_ENDPOINT = "/dpc/authorization/pdp"


def _make_request() -> httpx.Request:
    return httpx.Request("POST", f"{BASE_URL}{PDP_ENDPOINT}")


def _make_permit_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "Response": [
                {
                    "Decision": "Permit",
                    "Status": {
                        "StatusCode": {
                            "Value": "urn:oasis:names:tc:xacml:1.0:status:ok",
                        },
                    },
                },
            ],
        },
        request=_make_request(),
    )


def _make_permissions_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "Response": [
                {
                    "Decision": "Permit",
                    "Status": {"StatusCode": {"Value": "ok"}},
                    "Category": [
                        {
                            "CategoryId": "urn:oasis:names:tc:xacml:3.0:attribute-category:action",
                            "Attribute": [
                                {
                                    "AttributeId": "urn:oasis:names:tc:xacml:1.0:action:action-id",
                                    "Value": "VIEW",
                                },
                            ],
                        },
                    ],
                },
            ],
        },
        request=_make_request(),
    )


def _make_eval_request() -> EvalRequest:
    return EvalRequest(
        subject=Subject(id="user@example.com"),
        action=Action(id="VIEW"),
        resource=Resource(id="doc:1", type="documents"),
        application=Application(id="my-app"),
    )


def test_async_evaluate_returns_permit() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    when(mock_client).post(
        PDP_ENDPOINT,
        json=any_value(),
        headers=any_value(),
    ).thenReturn(_make_permit_response())

    pdp = AsyncPdpClient(
        base_url=BASE_URL,
        client_id="c",
        client_secret="s",
    )

    async def run() -> None:
        response = await pdp.evaluate(_make_eval_request())
        assert response.result.decision == Decision.PERMIT

    asyncio.run(run())


def test_async_permissions_returns_grouped() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    when(mock_client).post(
        PDP_ENDPOINT,
        json=any_value(),
        headers=any_value(),
    ).thenReturn(_make_permissions_response())

    pdp = AsyncPdpClient(
        base_url=BASE_URL,
        client_id="c",
        client_secret="s",
    )

    async def run() -> None:
        request = PermissionsRequest(
            subject=Subject(id="u"),
            resource=Resource(id="r", type="t"),
            application=Application(id="a"),
        )
        response = await pdp.permissions(request)
        assert len(response.allowed) == 1
        assert response.allowed[0].name == "VIEW"

    asyncio.run(run())


def test_async_context_manager_closes() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)
    when(mock_client).aclose().thenReturn(None)

    pdp = AsyncPdpClient(
        base_url=BASE_URL,
        client_id="c",
        client_secret="s",
    )

    async def run() -> None:
        await pdp.__aenter__()
        await pdp.__aexit__(None, None, None)

    asyncio.run(run())

    verify(mock_client).aclose()


def test_async_evaluate_with_xml() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    xml_response = (
        '<Response xmlns="urn:oasis:names:tc:xacml:3.0:core:schema:wd-17">'
        "<Result><Decision>Deny</Decision>"
        "<Status><StatusCode "
        'Value="urn:oasis:names:tc:xacml:1.0:status:ok"/>'
        "</Status></Result></Response>"
    )
    when(mock_client).post(
        PDP_ENDPOINT,
        content=any_value(bytes),
        headers={"Content-Type": "application/xml"},
    ).thenReturn(
        httpx.Response(
            200,
            content=xml_response.encode(),
            request=_make_request(),
        )
    )

    pdp = AsyncPdpClient(
        base_url=BASE_URL,
        client_id="c",
        client_secret="s",
    )

    async def run() -> None:
        response = await pdp.evaluate(
            _make_eval_request(),
            content_type=ContentType.XML,
        )
        assert response.result.decision == Decision.DENY

    asyncio.run(run())
