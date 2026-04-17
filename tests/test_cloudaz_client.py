from __future__ import annotations

import httpx
from mockito import mock, when, any as any_value, verify

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._component_search import ComponentSearchService
from nextlabs_sdk._cloudaz._component_type_search import ComponentTypeSearchService
from nextlabs_sdk._cloudaz._component_types import ComponentTypeService
from nextlabs_sdk._cloudaz._components import ComponentService
from nextlabs_sdk._cloudaz._operators import OperatorService
from nextlabs_sdk._cloudaz._policies import PolicyService
from nextlabs_sdk._cloudaz._policy_search import PolicySearchService
from nextlabs_sdk._cloudaz._tags import TagService
from nextlabs_sdk._config import HttpConfig, RetryConfig


def test_client_exposes_operator_service() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.operators, OperatorService)


def test_client_exposes_tag_service() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.tags, TagService)


def test_client_uses_custom_http_config() -> None:
    mock_client = mock(httpx.Client)
    custom_retry = RetryConfig(max_retries=5)
    custom_config = HttpConfig(timeout=60.0, verify_ssl=False, retry=custom_retry)

    when(transport_mod).create_http_client(
        base_url="https://cloudaz.example.com",
        auth=any_value(),
        http_config=custom_config,
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
        http_config=custom_config,
    )

    assert client.operators is not None


def test_client_context_manager_closes() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)
    when(mock_client).close().thenReturn(None)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )
    client.__enter__()
    client.__exit__(None, None, None)

    verify(mock_client).close()


def test_client_default_client_id() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert client.operators is not None


def test_client_exposes_component_type_service() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.component_types, ComponentTypeService)


def test_client_exposes_component_type_search_service() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.component_type_search, ComponentTypeSearchService)


def test_client_exposes_component_service() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.components, ComponentService)


def test_client_exposes_component_search_service() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.component_search, ComponentSearchService)


def test_client_exposes_policy_service() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.policies, PolicyService)


def test_client_exposes_policy_search_service() -> None:
    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.policy_search, PolicySearchService)


def test_client_exposes_reporter_audit_log_service() -> None:
    from nextlabs_sdk._cloudaz._reporter_audit_logs import ReporterAuditLogService

    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.reporter_audit_logs, ReporterAuditLogService)


def test_authenticate_invokes_auth_ensure_token() -> None:
    from nextlabs_sdk._auth._cloudaz_auth import CloudAzAuth

    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client._auth, CloudAzAuth)
    when(client._auth).ensure_token(any_value()).thenReturn(None)

    client.authenticate()

    verify(client._auth).ensure_token(any_value())


def test_authenticate_raises_when_custom_auth_override() -> None:
    from nextlabs_sdk.exceptions import AuthenticationError

    mock_client = mock(httpx.Client)
    when(transport_mod).create_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)

    custom = mock(httpx.Auth)
    client = CloudAzClient(
        base_url="https://cloudaz.example.com",
        auth=custom,
    )

    try:
        client.authenticate()
    except AuthenticationError as exc:
        assert "custom auth" in exc.message.lower()
    else:
        raise AssertionError("expected AuthenticationError")
