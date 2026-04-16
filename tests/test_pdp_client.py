from __future__ import annotations

import httpx
import pytest
from mockito import mock, when, any as any_value, verify

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._config import HttpConfig, RetryConfig
from nextlabs_sdk._pdp._client import PdpClient
from nextlabs_sdk._pdp._enums import ContentType, Decision
from nextlabs_sdk._pdp._request_models import (
    Action,
    Application,
    EvalRequest,
    PermissionsRequest,
    Resource,
    Subject,
)
from nextlabs_sdk.exceptions import ValidationError

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
                {
                    "Decision": "Deny",
                    "Status": {"StatusCode": {"Value": "ok"}},
                    "Category": [
                        {
                            "CategoryId": "urn:oasis:names:tc:xacml:3.0:attribute-category:action",
                            "Attribute": [
                                {
                                    "AttributeId": "urn:oasis:names:tc:xacml:1.0:action:action-id",
                                    "Value": "DELETE",
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


def _make_permissions_request() -> PermissionsRequest:
    return PermissionsRequest(
        subject=Subject(id="user@example.com"),
        resource=Resource(id="doc:1", type="documents"),
        application=Application(id="my-app"),
    )


def test_evaluate_returns_permit() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
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

    pdp = PdpClient(
        base_url=BASE_URL,
        client_id="my-client",
        client_secret="my-secret",
    )
    response = pdp.evaluate(_make_eval_request())

    assert response.result.decision == Decision.PERMIT


def test_evaluate_posts_to_correct_endpoint() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
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

    pdp = PdpClient(
        base_url=BASE_URL,
        client_id="c",
        client_secret="s",
    )
    pdp.evaluate(_make_eval_request())

    verify(mock_client).post(
        PDP_ENDPOINT,
        json=any_value(),
        headers=any_value(),
    )


def test_evaluate_sets_json_content_type_header() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    when(mock_client).post(
        PDP_ENDPOINT,
        json=any_value(),
        headers={"Content-Type": "application/json"},
    ).thenReturn(_make_permit_response())

    pdp = PdpClient(
        base_url=BASE_URL,
        client_id="c",
        client_secret="s",
    )
    pdp.evaluate(_make_eval_request(), content_type=ContentType.JSON)

    verify(mock_client).post(
        PDP_ENDPOINT,
        json=any_value(),
        headers={"Content-Type": "application/json"},
    )


def test_permissions_returns_grouped_actions() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
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

    pdp = PdpClient(
        base_url=BASE_URL,
        client_id="c",
        client_secret="s",
    )
    response = pdp.permissions(_make_permissions_request())

    assert len(response.allowed) == 1
    assert response.allowed[0].name == "VIEW"
    assert len(response.denied) == 1
    assert response.denied[0].name == "DELETE"


def test_client_uses_custom_http_config() -> None:
    mock_client = mock(httpx.Client)
    custom_retry = RetryConfig(max_retries=5)
    custom_config = HttpConfig(timeout=60.0, verify_ssl=False, retry=custom_retry)

    when(transport_mod).create_http_client(
        base_url=BASE_URL,
        auth=any_value(),
        timeout=60.0,
        verify_ssl=False,
        retry=custom_retry,
    ).thenReturn(mock_client)

    pdp = PdpClient(
        base_url=BASE_URL,
        client_id="c",
        client_secret="s",
        http_config=custom_config,
    )

    assert pdp is not None


def test_client_context_manager_closes() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)
    when(mock_client).close().thenReturn(None)

    pdp = PdpClient(
        base_url=BASE_URL,
        client_id="c",
        client_secret="s",
    )
    pdp.__enter__()
    pdp.__exit__(None, None, None)

    verify(mock_client).close()


def test_evaluate_raises_on_400() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
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
    ).thenReturn(
        httpx.Response(
            400,
            json={"error": "bad request"},
            request=_make_request(),
        )
    )

    pdp = PdpClient(
        base_url=BASE_URL,
        client_id="c",
        client_secret="s",
    )

    with pytest.raises(ValidationError):
        pdp.evaluate(_make_eval_request())


def test_evaluate_with_xml_content_type() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    xml_response_body = (
        '<Response xmlns="urn:oasis:names:tc:xacml:3.0:core:schema:wd-17">'
        "<Result>"
        "<Decision>Permit</Decision>"
        "<Status><StatusCode "
        'Value="urn:oasis:names:tc:xacml:1.0:status:ok"/>'
        "</Status>"
        "</Result>"
        "</Response>"
    )
    when(mock_client).post(
        PDP_ENDPOINT,
        content=any_value(bytes),
        headers={"Content-Type": "application/xml"},
    ).thenReturn(
        httpx.Response(
            200,
            content=xml_response_body.encode(),
            request=_make_request(),
        )
    )

    pdp = PdpClient(
        base_url=BASE_URL,
        client_id="c",
        client_secret="s",
    )
    response = pdp.evaluate(
        _make_eval_request(),
        content_type=ContentType.XML,
    )

    assert response.result.decision == Decision.PERMIT
