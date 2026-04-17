from __future__ import annotations

import asyncio
from typing import Any, Coroutine, TypeVar, cast

import httpx
import pytest
from mockito import any as any_value, mock, verify, when

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._cloudaz._async_client import AsyncCloudAzClient
from nextlabs_sdk._cloudaz._component_search import AsyncComponentSearchService
from nextlabs_sdk._cloudaz._component_type_search import AsyncComponentTypeSearchService
from nextlabs_sdk._cloudaz._component_types import AsyncComponentTypeService
from nextlabs_sdk._cloudaz._components import AsyncComponentService
from nextlabs_sdk._cloudaz._operators import AsyncOperatorService
from nextlabs_sdk._cloudaz._policies import AsyncPolicyService
from nextlabs_sdk._cloudaz._policy_search import AsyncPolicySearchService
from nextlabs_sdk._cloudaz._reporter_audit_logs import AsyncReporterAuditLogService
from nextlabs_sdk._cloudaz._tags import AsyncTagService
from nextlabs_sdk._config import HttpConfig

T = TypeVar("T")

BASE_URL = "https://cloudaz.example.com"


def _run_async(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


def _stub_transport() -> httpx.AsyncClient:
    mock_client = mock(httpx.AsyncClient)
    when(transport_mod).create_async_http_client(
        base_url=any_value(),
        auth=any_value(),
        http_config=any_value(),
    ).thenReturn(mock_client)
    return cast(httpx.AsyncClient, mock_client)


def _make_client(**kwargs: Any) -> AsyncCloudAzClient:
    defaults: dict[str, Any] = {
        "base_url": BASE_URL,
        "username": "admin",
        "password": "secret",
    }
    defaults.update(kwargs)
    return AsyncCloudAzClient(**defaults)


@pytest.mark.parametrize(
    "attr,service_cls",
    [
        pytest.param("operators", AsyncOperatorService, id="operators"),
        pytest.param("tags", AsyncTagService, id="tags"),
        pytest.param(
            "component_types", AsyncComponentTypeService, id="component-types"
        ),
        pytest.param(
            "component_type_search",
            AsyncComponentTypeSearchService,
            id="component-type-search",
        ),
        pytest.param("components", AsyncComponentService, id="components"),
        pytest.param(
            "component_search", AsyncComponentSearchService, id="component-search"
        ),
        pytest.param("policies", AsyncPolicyService, id="policies"),
        pytest.param("policy_search", AsyncPolicySearchService, id="policy-search"),
        pytest.param(
            "reporter_audit_logs",
            AsyncReporterAuditLogService,
            id="reporter-audit-logs",
        ),
    ],
)
def test_async_client_exposes_service(attr, service_cls):
    _stub_transport()
    client = _make_client()
    assert isinstance(getattr(client, attr), service_cls)


def test_async_client_uses_custom_config():
    mock_client = mock(httpx.AsyncClient)
    custom_config = HttpConfig(timeout=60.0, verify_ssl=False)

    when(transport_mod).create_async_http_client(
        base_url=BASE_URL,
        auth=any_value(),
        http_config=custom_config,
    ).thenReturn(mock_client)

    client = _make_client(http_config=custom_config)

    assert client.operators is not None


def test_async_client_context_manager_closes():
    mock_client = _stub_transport()
    when(mock_client).aclose().thenReturn(None)

    async def run() -> None:
        client = _make_client()
        await client.__aenter__()
        await client.__aexit__(None, None, None)

    _run_async(run())

    verify(mock_client).aclose()


def test_async_authenticate_invokes_ensure_token_async():
    from nextlabs_sdk._auth._cloudaz_auth import CloudAzAuth

    _stub_transport()
    client = _make_client()
    assert isinstance(client._auth, CloudAzAuth)
    when(client._auth).ensure_token_async(any_value()).thenReturn(asyncio.sleep(0))
    _run_async(client.authenticate())
    verify(client._auth).ensure_token_async(any_value())


def test_async_authenticate_raises_when_custom_auth():
    from nextlabs_sdk.exceptions import AuthenticationError

    _stub_transport()
    custom = mock(httpx.Auth)
    client = AsyncCloudAzClient(base_url=BASE_URL, auth=custom)

    async def run() -> None:
        await client.authenticate()

    try:
        _run_async(run())
    except AuthenticationError as exc:
        assert "custom auth" in exc.message.lower()
    else:
        raise AssertionError("expected AuthenticationError")
