from __future__ import annotations

import asyncio

import httpx
from mockito import mock, when, any as any_value, verify

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._cloudaz._async_client import AsyncCloudAzClient
from nextlabs_sdk._cloudaz._component_search import AsyncComponentSearchService
from nextlabs_sdk._cloudaz._component_type_search import AsyncComponentTypeSearchService
from nextlabs_sdk._cloudaz._component_types import AsyncComponentTypeService
from nextlabs_sdk._cloudaz._components import AsyncComponentService
from nextlabs_sdk._cloudaz._operators import AsyncOperatorService
from nextlabs_sdk._cloudaz._policies import AsyncPolicyService
from nextlabs_sdk._cloudaz._policy_search import AsyncPolicySearchService
from nextlabs_sdk._cloudaz._tags import AsyncTagService
from nextlabs_sdk._config import HttpConfig


def test_async_client_exposes_operator_service() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    client = AsyncCloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.operators, AsyncOperatorService)


def test_async_client_exposes_tag_service() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    client = AsyncCloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.tags, AsyncTagService)


def test_async_client_uses_custom_config() -> None:
    mock_client = mock(httpx.AsyncClient)
    custom_config = HttpConfig(timeout=60.0, verify_ssl=False)

    when(transport_mod).create_async_http_client(
        base_url="https://cloudaz.example.com",
        auth=any_value(),
        timeout=60.0,
        verify_ssl=False,
        retry=any_value(),
    ).thenReturn(mock_client)

    client = AsyncCloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
        http_config=custom_config,
    )

    assert client.operators is not None


def test_async_client_context_manager_closes() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)
    when(mock_client).aclose().thenReturn(None)

    async def run() -> None:
        client = AsyncCloudAzClient(
            base_url="https://cloudaz.example.com",
            username="admin",
            password="secret",
        )
        await client.__aenter__()
        await client.__aexit__(None, None, None)

    asyncio.run(run())

    verify(mock_client).aclose()


def test_async_client_exposes_component_type_service() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    client = AsyncCloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.component_types, AsyncComponentTypeService)


def test_async_client_exposes_component_type_search_service() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    client = AsyncCloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.component_type_search, AsyncComponentTypeSearchService)


def test_async_client_exposes_component_service() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    client = AsyncCloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.components, AsyncComponentService)


def test_async_client_exposes_component_search_service() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    client = AsyncCloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.component_search, AsyncComponentSearchService)


def test_async_client_exposes_policy_service() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    client = AsyncCloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.policies, AsyncPolicyService)


def test_async_client_exposes_policy_search_service() -> None:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    client = AsyncCloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.policy_search, AsyncPolicySearchService)


def test_async_client_exposes_reporter_audit_log_service() -> None:
    from nextlabs_sdk._cloudaz._reporter_audit_logs import AsyncReporterAuditLogService

    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        timeout=any_value(),
        verify_ssl=any_value(),
        retry=any_value(),
    ).thenReturn(mock_client)

    client = AsyncCloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    )

    assert isinstance(client.reporter_audit_logs, AsyncReporterAuditLogService)
