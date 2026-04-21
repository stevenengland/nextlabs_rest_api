from __future__ import annotations

import asyncio
from typing import Any, Awaitable, TypeVar

import httpx
import pytest
from mockito import any as any_value, mock, verify, when

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
from nextlabs_sdk.exceptions import ApiError

BASE_URL = "https://pdp.example.com"
PDP_ENDPOINT = "/dpc/authorization/pdp"

T = TypeVar("T")


def _run_async(coro: Awaitable[T]) -> T:
    return asyncio.run(coro)  # type: ignore[arg-type]


def _make_request() -> httpx.Request:
    return httpx.Request("POST", f"{BASE_URL}{PDP_ENDPOINT}")


def _stub_transport() -> Any:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)
    return mock_client


def _make_pdp() -> AsyncPdpClient:
    return AsyncPdpClient(base_url=BASE_URL, client_id="c", client_secret="s")


def _permit_response() -> httpx.Response:
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


def _permissions_response() -> httpx.Response:
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


def _eval_request() -> EvalRequest:
    return EvalRequest(
        subject=Subject(id="user@example.com"),
        action=Action(id="VIEW"),
        resource=Resource(id="doc:1", type="documents"),
        application=Application(id="my-app"),
    )


def _stub_post_json(mock_client: Any, response: httpx.Response) -> None:
    when(mock_client).post(
        PDP_ENDPOINT,
        json=any_value(),
        headers=any_value(),
    ).thenReturn(response)


def test_async_evaluate_returns_permit():
    mock_client = _stub_transport()
    _stub_post_json(mock_client, _permit_response())
    pdp = _make_pdp()

    async def run() -> None:
        response = await pdp.evaluate(_eval_request())
        assert response.first_result.decision == Decision.PERMIT

    _run_async(run())


def test_async_permissions_returns_grouped():
    mock_client = _stub_transport()
    _stub_post_json(mock_client, _permissions_response())
    pdp = _make_pdp()

    async def run() -> None:
        request = PermissionsRequest(
            subject=Subject(id="u"),
            resource=Resource(id="r", type="t"),
            application=Application(id="a"),
        )
        response = await pdp.permissions(request)
        assert len(response.allowed) == 1
        assert response.allowed[0].name == "VIEW"

    _run_async(run())


def test_async_context_manager_closes():
    mock_client = _stub_transport()
    when(mock_client).aclose().thenReturn(None)
    pdp = _make_pdp()

    async def run() -> None:
        await pdp.__aenter__()
        await pdp.__aexit__(None, None, None)

    _run_async(run())
    verify(mock_client).aclose()


def test_async_evaluate_with_xml():
    mock_client = _stub_transport()
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
        httpx.Response(200, content=xml_response.encode(), request=_make_request()),
    )
    pdp = _make_pdp()

    async def run() -> None:
        response = await pdp.evaluate(_eval_request(), content_type=ContentType.XML)
        assert response.first_result.decision == Decision.DENY

    _run_async(run())


def test_async_evaluate_raises_api_error_on_non_json_response():
    mock_client = _stub_transport()
    _stub_post_json(
        mock_client,
        httpx.Response(200, content=b"<html>oops</html>", request=_make_request()),
    )
    pdp = _make_pdp()

    async def run() -> None:
        with pytest.raises(ApiError) as exc_info:
            await pdp.evaluate(_eval_request())
        assert "Invalid JSON response" in exc_info.value.message

    _run_async(run())


def test_async_permissions_raises_api_error_on_unexpected_shape():
    mock_client = _stub_transport()
    _stub_post_json(
        mock_client,
        httpx.Response(200, json={"nope": True}, request=_make_request()),
    )
    pdp = _make_pdp()

    async def run() -> None:
        with pytest.raises(ApiError) as exc_info:
            await pdp.permissions(
                PermissionsRequest(
                    subject=Subject(id="u"),
                    action=Action(id="VIEW"),
                    resource=Resource(id="r", type="doc"),
                    application=Application(id="app"),
                ),
            )
        assert "Unexpected PDP response shape" in exc_info.value.message

    _run_async(run())


def test_async_pdp_client_defaults_token_url_to_dpc_oauth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _capture(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return mock(httpx.AsyncClient)

    monkeypatch.setattr(transport_mod, "create_async_http_client", _capture)

    AsyncPdpClient(base_url=BASE_URL, client_id="c", client_secret="s")

    assert captured["auth"]._token_url == f"{BASE_URL}/dpc/oauth"


def test_async_pdp_client_uses_auth_base_url_for_cas_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _capture(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return mock(httpx.AsyncClient)

    monkeypatch.setattr(transport_mod, "create_async_http_client", _capture)

    AsyncPdpClient(
        base_url=BASE_URL,
        client_id="c",
        client_secret="s",
        auth_base_url="https://cloudaz.example.com",
    )

    assert captured["auth"]._token_url == "https://cloudaz.example.com/cas/token"


def test_async_pdp_client_explicit_token_url_overrides_auth_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _capture(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return mock(httpx.AsyncClient)

    monkeypatch.setattr(transport_mod, "create_async_http_client", _capture)

    AsyncPdpClient(
        base_url=BASE_URL,
        client_id="c",
        client_secret="s",
        auth_base_url="https://cloudaz.example.com",
        token_url="https://override.example.com/oauth",
    )

    assert captured["auth"]._token_url == "https://override.example.com/oauth"
