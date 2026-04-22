from __future__ import annotations

from types import MappingProxyType
from typing import Any, cast

import httpx
import pytest
from mockito import any as any_value, mock, verify, when

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
from nextlabs_sdk.exceptions import ApiError, NextLabsError, ValidationError

BASE_URL = "https://pdp.example.com"
PDP_ENDPOINT = "/dpc/authorization/pdp"
PERMISSIONS_ENDPOINT = "/dpc/authorization/pdppermissions"

JSON_HEADERS = MappingProxyType(
    {
        "Content-Type": "application/json",
        "Service": "EVAL",
        "Version": "1.0",
    }
)
XML_HEADERS = MappingProxyType(
    {
        "Content-Type": "application/xml",
        "Service": "EVAL",
        "Version": "1.0",
    }
)


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
                            "Value": "urn:oasis:names:tc:xacml:1.0:status:ok"
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
            "Status": {
                "StatusCode": {"Value": "urn:oasis:names:tc:xacml:1.0:status:ok"}
            },
            "Response": [
                {
                    "ActionsAndObligations": {
                        "allow": [
                            {
                                "Action": "VIEW",
                                "MatchingPolicies": ["ROOT/VIEW Policy"],
                                "Obligations": [],
                            },
                        ],
                        "deny": [
                            {
                                "Action": "DELETE",
                                "MatchingPolicies": ["ROOT/DELETE Policy"],
                                "Obligations": [],
                            },
                        ],
                        "dontcare": [],
                    },
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


def _stub_transport(http_config: Any = None) -> httpx.Client:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value() if http_config is None else BASE_URL,
        auth=any_value(),
        http_config=any_value() if http_config is None else http_config,
    ).thenReturn(mock_client)
    return cast(httpx.Client, mock_client)


def _make_pdp(**kwargs: Any) -> PdpClient:
    defaults: dict[str, Any] = {
        "base_url": BASE_URL,
        "client_id": "c",
        "client_secret": "s",
    }
    defaults.update(kwargs)
    return PdpClient(**defaults)


def test_evaluate_returns_permit():
    mock_client = _stub_transport()
    when(mock_client).post(
        PDP_ENDPOINT,
        json=any_value(),
        headers=any_value(),
    ).thenReturn(_make_permit_response())

    response = _make_pdp().evaluate(_make_eval_request())

    assert response.first_result.decision == Decision.PERMIT


def test_evaluate_posts_to_correct_endpoint():
    mock_client = _stub_transport()
    when(mock_client).post(
        PDP_ENDPOINT,
        json=any_value(),
        headers=any_value(),
    ).thenReturn(_make_permit_response())

    _make_pdp().evaluate(_make_eval_request())

    verify(mock_client).post(PDP_ENDPOINT, json=any_value(), headers=any_value())


def test_evaluate_sets_json_content_type_header():
    mock_client = _stub_transport()
    when(mock_client).post(
        PDP_ENDPOINT,
        json=any_value(),
        headers=JSON_HEADERS,
    ).thenReturn(_make_permit_response())

    _make_pdp().evaluate(_make_eval_request(), content_type=ContentType.JSON)

    verify(mock_client).post(
        PDP_ENDPOINT,
        json=any_value(),
        headers=JSON_HEADERS,
    )


def test_permissions_returns_grouped_actions():
    mock_client = _stub_transport()
    when(mock_client).post(
        PERMISSIONS_ENDPOINT,
        json=any_value(),
        headers=any_value(),
    ).thenReturn(_make_permissions_response())

    response = _make_pdp().permissions(_make_permissions_request())

    assert len(response.allowed) == 1
    assert response.allowed[0].name == "VIEW"
    assert response.allowed[0].policy_refs[0].id == "ROOT/VIEW Policy"
    assert len(response.denied) == 1
    assert response.denied[0].name == "DELETE"


def test_permissions_posts_to_permissions_endpoint():
    mock_client = _stub_transport()
    when(mock_client).post(
        PERMISSIONS_ENDPOINT,
        json=any_value(),
        headers=any_value(),
    ).thenReturn(_make_permissions_response())

    _make_pdp().permissions(_make_permissions_request())

    verify(mock_client).post(
        PERMISSIONS_ENDPOINT,
        json=any_value(),
        headers=any_value(),
    )


def test_client_uses_custom_http_config():
    custom_retry = RetryConfig(max_retries=5)
    custom_config = HttpConfig(timeout=60.0, verify_ssl=False, retry=custom_retry)
    _stub_transport(http_config=custom_config)

    pdp = _make_pdp(http_config=custom_config)

    assert pdp is not None


def test_client_context_manager_closes():
    mock_client = _stub_transport()
    when(mock_client).close().thenReturn(None)

    pdp = _make_pdp()
    pdp.__enter__()
    pdp.__exit__(None, None, None)

    verify(mock_client).close()


def test_evaluate_with_xml_content_type():
    mock_client = _stub_transport()
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
        headers=XML_HEADERS,
    ).thenReturn(
        httpx.Response(
            200, content=xml_response_body.encode(), request=_make_request()
        ),
    )

    response = _make_pdp().evaluate(_make_eval_request(), content_type=ContentType.XML)

    assert response.first_result.decision == Decision.PERMIT


@pytest.mark.parametrize(
    "response,expected_exc,match",
    [
        pytest.param(
            httpx.Response(400, json={"error": "bad request"}, request=_make_request()),
            ValidationError,
            None,
            id="evaluate-400-validation-error",
        ),
        pytest.param(
            httpx.Response(200, content=b"<html>oops</html>", request=_make_request()),
            ApiError,
            "Invalid JSON response",
            id="evaluate-non-json-body",
        ),
        pytest.param(
            httpx.Response(200, json={"nope": True}, request=_make_request()),
            ApiError,
            "Unexpected PDP response shape",
            id="evaluate-unexpected-shape",
        ),
    ],
)
def test_evaluate_error_dispatch(response, expected_exc, match):
    mock_client = _stub_transport()
    when(mock_client).post(
        PDP_ENDPOINT,
        json=any_value(),
        headers=any_value(),
    ).thenReturn(response)

    pdp = _make_pdp()
    with pytest.raises(expected_exc) as exc_info:
        pdp.evaluate(_make_eval_request())
    if match is not None:
        assert match in exc_info.value.message


def test_permissions_raises_api_error_on_non_json_response():
    mock_client = _stub_transport()
    when(mock_client).post(
        PERMISSIONS_ENDPOINT,
        json=any_value(),
        headers=any_value(),
    ).thenReturn(httpx.Response(200, content=b"x", request=_make_request()))

    with pytest.raises(ApiError):
        _make_pdp().permissions(_make_permissions_request())


def test_pdp_client_defaults_token_url_to_dpc_oauth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _capture(**kwargs: Any) -> httpx.Client:
        captured.update(kwargs)
        return cast(httpx.Client, mock(httpx.Client))

    monkeypatch.setattr(transport_mod, "create_http_client", _capture)

    _make_pdp()

    assert captured["auth"]._token_url == f"{BASE_URL}/dpc/oauth"


def test_pdp_client_uses_auth_base_url_for_cas_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _capture(**kwargs: Any) -> httpx.Client:
        captured.update(kwargs)
        return cast(httpx.Client, mock(httpx.Client))

    monkeypatch.setattr(transport_mod, "create_http_client", _capture)

    _make_pdp(auth_base_url="https://cloudaz.example.com")

    assert captured["auth"]._token_url == "https://cloudaz.example.com/cas/token"


def test_pdp_client_explicit_token_url_overrides_auth_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _capture(**kwargs: Any) -> httpx.Client:
        captured.update(kwargs)
        return cast(httpx.Client, mock(httpx.Client))

    monkeypatch.setattr(transport_mod, "create_http_client", _capture)

    _make_pdp(
        auth_base_url="https://cloudaz.example.com",
        token_url="https://override.example.com/oauth",
    )

    assert captured["auth"]._token_url == "https://override.example.com/oauth"


def _raw_xacml_body() -> dict[str, Any]:
    return {
        "Request": {
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
    }


def test_evaluate_raw_posts_body_verbatim() -> None:
    mock_client = _stub_transport()
    when(mock_client).post(
        PDP_ENDPOINT,
        json=_raw_xacml_body(),
        headers=JSON_HEADERS,
    ).thenReturn(_make_permit_response())

    response = _make_pdp().evaluate_raw(_raw_xacml_body())

    assert response.first_result.decision == Decision.PERMIT
    verify(mock_client).post(
        PDP_ENDPOINT,
        json=_raw_xacml_body(),
        headers=JSON_HEADERS,
    )


def test_permissions_raw_posts_body_verbatim() -> None:
    mock_client = _stub_transport()
    when(mock_client).post(
        PERMISSIONS_ENDPOINT,
        json=_raw_xacml_body(),
        headers=JSON_HEADERS,
    ).thenReturn(_make_permissions_response())

    response = _make_pdp().permissions_raw(_raw_xacml_body())

    assert len(response.allowed) == 1


def test_evaluate_raw_rejects_xml_content_type() -> None:
    _stub_transport()
    with pytest.raises(
        NextLabsError, match="evaluate_raw.*only supports ContentType.JSON"
    ):
        _make_pdp().evaluate_raw(_raw_xacml_body(), content_type=ContentType.XML)


def test_permissions_raw_rejects_xml_content_type() -> None:
    _stub_transport()
    with pytest.raises(
        NextLabsError, match="permissions_raw.*only supports ContentType.JSON"
    ):
        _make_pdp().permissions_raw(_raw_xacml_body(), content_type=ContentType.XML)


def test_permissions_sends_service_and_version_headers() -> None:
    mock_client = _stub_transport()
    when(mock_client).post(
        PERMISSIONS_ENDPOINT,
        json=any_value(),
        headers=JSON_HEADERS,
    ).thenReturn(_make_permissions_response())

    _make_pdp().permissions(_make_permissions_request())

    verify(mock_client).post(
        PERMISSIONS_ENDPOINT,
        json=any_value(),
        headers=JSON_HEADERS,
    )


def test_custom_service_and_version_headers_propagate() -> None:
    mock_client = _stub_transport()
    custom_headers = {
        "Content-Type": "application/json",
        "Service": "CUSTOM",
        "Version": "2.0",
    }
    when(mock_client).post(
        PDP_ENDPOINT,
        json=any_value(),
        headers=custom_headers,
    ).thenReturn(_make_permit_response())

    _make_pdp(service="CUSTOM", version="2.0").evaluate(_make_eval_request())

    verify(mock_client).post(
        PDP_ENDPOINT,
        json=any_value(),
        headers=custom_headers,
    )
