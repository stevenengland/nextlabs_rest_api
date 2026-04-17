from __future__ import annotations

import httpx
import pytest
from mockito import any as any_value, mock, verify, when

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._config import HttpConfig
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._component_search import ComponentSearchService
from nextlabs_sdk._cloudaz._component_type_search import ComponentTypeSearchService
from nextlabs_sdk._cloudaz._component_types import ComponentTypeService
from nextlabs_sdk._cloudaz._components import ComponentService
from nextlabs_sdk._cloudaz._operators import OperatorService
from nextlabs_sdk._cloudaz._policies import PolicyService
from nextlabs_sdk._cloudaz._policy_search import PolicySearchService
from nextlabs_sdk._cloudaz._reporter_audit_logs import ReporterAuditLogService
from nextlabs_sdk._cloudaz._tags import TagService

BASE_URL = "https://cloudaz.example.com"


def _stub_transport(http_config: object = None) -> object:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value() if http_config is None else http_config,
    ).thenReturn(mock_client)
    return mock_client


def _make_client(http_config: HttpConfig | None = None) -> CloudAzClient:
    if http_config is None:
        return CloudAzClient(base_url=BASE_URL, username="admin", password="secret")
    return CloudAzClient(
        base_url=BASE_URL,
        username="admin",
        password="secret",
        http_config=http_config,
    )


@pytest.mark.parametrize(
    "attr,service_cls",
    [
        pytest.param("operators", OperatorService, id="operators"),
        pytest.param("tags", TagService, id="tags"),
        pytest.param("component_types", ComponentTypeService, id="component-types"),
        pytest.param(
            "component_type_search",
            ComponentTypeSearchService,
            id="component-type-search",
        ),
        pytest.param("components", ComponentService, id="components"),
        pytest.param("component_search", ComponentSearchService, id="component-search"),
        pytest.param("policies", PolicyService, id="policies"),
        pytest.param("policy_search", PolicySearchService, id="policy-search"),
        pytest.param(
            "reporter_audit_logs", ReporterAuditLogService, id="reporter-audit-logs"
        ),
    ],
)
def test_client_exposes_service(attr, service_cls):
    _stub_transport()
    client = _make_client()
    assert isinstance(getattr(client, attr), service_cls)


def test_client_uses_custom_http_config():
    from nextlabs_sdk._config import RetryConfig

    custom_retry = RetryConfig(max_retries=5)
    custom_config = HttpConfig(timeout=60.0, verify_ssl=False, retry=custom_retry)
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=BASE_URL,
        auth=any_value(),
        http_config=custom_config,
    ).thenReturn(mock_client)

    client = _make_client(http_config=custom_config)
    assert client.operators is not None


def test_client_context_manager_closes():
    mock_client = _stub_transport()
    when(mock_client).close().thenReturn(None)

    client = _make_client()
    client.__enter__()
    client.__exit__(None, None, None)

    verify(mock_client).close()


def test_client_default_client_id():
    _stub_transport()
    client = _make_client()
    assert client.operators is not None


def test_authenticate_invokes_auth_ensure_token():
    from nextlabs_sdk._auth._cloudaz_auth import CloudAzAuth

    _stub_transport()
    client = _make_client()

    assert isinstance(client._auth, CloudAzAuth)
    when(client._auth).ensure_token(any_value()).thenReturn(None)

    client.authenticate()

    verify(client._auth).ensure_token(any_value())


def test_authenticate_raises_when_custom_auth_override():
    from nextlabs_sdk.exceptions import AuthenticationError

    _stub_transport()
    custom = mock(httpx.Auth)
    client = CloudAzClient(base_url=BASE_URL, auth=custom)

    try:
        client.authenticate()
    except AuthenticationError as exc:
        assert "custom auth" in exc.message.lower()
    else:
        raise AssertionError("expected AuthenticationError")
