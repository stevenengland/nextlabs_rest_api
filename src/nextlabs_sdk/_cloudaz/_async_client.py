from __future__ import annotations

from types import TracebackType

import httpx

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._auth._cloudaz_auth import CloudAzAuth
from nextlabs_sdk._auth._token_cache._null_token_cache import NullTokenCache
from nextlabs_sdk._auth._token_cache._token_cache import TokenCache
from nextlabs_sdk._cloudaz._component_search import AsyncComponentSearchService
from nextlabs_sdk._cloudaz._component_type_search import AsyncComponentTypeSearchService
from nextlabs_sdk._cloudaz._component_types import AsyncComponentTypeService
from nextlabs_sdk._cloudaz._components import AsyncComponentService
from nextlabs_sdk._cloudaz._operators import AsyncOperatorService
from nextlabs_sdk._cloudaz._policies import AsyncPolicyService
from nextlabs_sdk._cloudaz._policy_search import AsyncPolicySearchService
from nextlabs_sdk._cloudaz._activity_logs_service import AsyncReportActivityLogService
from nextlabs_sdk._cloudaz._audit_logs import AsyncEntityAuditLogService
from nextlabs_sdk._cloudaz._dashboard import AsyncDashboardService
from nextlabs_sdk._cloudaz._reports import AsyncPolicyActivityReportService
from nextlabs_sdk._cloudaz._reporter_audit_logs import AsyncReporterAuditLogService
from nextlabs_sdk._cloudaz._system_config import AsyncSystemConfigService
from nextlabs_sdk._cloudaz._tags import AsyncTagService
from nextlabs_sdk._config import HttpConfig


class AsyncCloudAzClient:
    """Asynchronous client for the NextLabs CloudAz Console API."""

    def __init__(
        self,
        *,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
        client_id: str = "ControlCenterOIDCClient",
        http_config: HttpConfig | None = None,
        token_cache: TokenCache | None = None,
        auth: httpx.Auth | None = None,
    ) -> None:
        config = http_config or HttpConfig()
        if auth is None:
            if username is None:
                raise ValueError(
                    "username is required when no auth override is provided",
                )
            cache = token_cache or NullTokenCache()
            auth = CloudAzAuth(
                token_url=f"{base_url}/cas/oidc/accessToken",
                username=username,
                password=password,
                client_id=client_id,
                token_cache=cache,
            )
        self._client = transport_mod.create_async_http_client(
            base_url=base_url,
            auth=auth,
            timeout=config.timeout,
            verify_ssl=config.verify_ssl,
            retry=config.retry,
        )
        self._operators = AsyncOperatorService(self._client)
        self._tags = AsyncTagService(self._client)
        self._component_types = AsyncComponentTypeService(self._client)
        self._component_type_search = AsyncComponentTypeSearchService(self._client)
        self._components = AsyncComponentService(self._client)
        self._component_search = AsyncComponentSearchService(self._client)
        self._policies = AsyncPolicyService(self._client)
        self._policy_search = AsyncPolicySearchService(self._client)
        self._audit_logs = AsyncEntityAuditLogService(self._client)
        self._system_config = AsyncSystemConfigService(self._client)
        self._reports = AsyncPolicyActivityReportService(self._client)
        self._activity_logs = AsyncReportActivityLogService(self._client)
        self._dashboard = AsyncDashboardService(self._client)
        self._reporter_audit_logs = AsyncReporterAuditLogService(self._client)

    @property
    def operators(self) -> AsyncOperatorService:
        return self._operators

    @property
    def tags(self) -> AsyncTagService:
        return self._tags

    @property
    def component_types(self) -> AsyncComponentTypeService:
        return self._component_types

    @property
    def component_type_search(self) -> AsyncComponentTypeSearchService:
        return self._component_type_search

    @property
    def components(self) -> AsyncComponentService:
        return self._components

    @property
    def component_search(self) -> AsyncComponentSearchService:
        return self._component_search

    @property
    def policies(self) -> AsyncPolicyService:
        return self._policies

    @property
    def policy_search(self) -> AsyncPolicySearchService:
        return self._policy_search

    @property
    def audit_logs(self) -> AsyncEntityAuditLogService:
        return self._audit_logs

    @property
    def system_config(self) -> AsyncSystemConfigService:
        return self._system_config

    @property
    def reports(self) -> AsyncPolicyActivityReportService:
        return self._reports

    @property
    def activity_logs(self) -> AsyncReportActivityLogService:
        return self._activity_logs

    @property
    def dashboard(self) -> AsyncDashboardService:
        return self._dashboard

    @property
    def reporter_audit_logs(self) -> AsyncReporterAuditLogService:
        return self._reporter_audit_logs

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncCloudAzClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()
