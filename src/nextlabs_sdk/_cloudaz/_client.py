from __future__ import annotations

from types import TracebackType

import httpx

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._auth._cloudaz_auth import CloudAzAuth
from nextlabs_sdk._auth._token_cache._null_token_cache import NullTokenCache
from nextlabs_sdk._auth._token_cache._token_cache import TokenCache
from nextlabs_sdk._cloudaz._component_search import ComponentSearchService
from nextlabs_sdk._cloudaz._component_type_search import ComponentTypeSearchService
from nextlabs_sdk._cloudaz._component_types import ComponentTypeService
from nextlabs_sdk._cloudaz._components import ComponentService
from nextlabs_sdk._cloudaz._operators import OperatorService
from nextlabs_sdk._cloudaz._policies import PolicyService
from nextlabs_sdk._cloudaz._policy_search import PolicySearchService
from nextlabs_sdk._cloudaz._activity_logs_service import ReportActivityLogService
from nextlabs_sdk._cloudaz._audit_logs import EntityAuditLogService
from nextlabs_sdk._cloudaz._dashboard import DashboardService
from nextlabs_sdk._cloudaz._reports import PolicyActivityReportService
from nextlabs_sdk._cloudaz._reporter_audit_logs import ReporterAuditLogService
from nextlabs_sdk._cloudaz._system_config import SystemConfigService
from nextlabs_sdk._cloudaz._tags import TagService
from nextlabs_sdk._config import HttpConfig
from nextlabs_sdk.exceptions import AuthenticationError


class CloudAzClient:  # noqa: WPS214
    """Synchronous client for the NextLabs CloudAz Console API."""

    def __init__(  # noqa: WPS211
        self,
        *,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
        client_id: str = "ControlCenterOIDCClient",
        http_config: HttpConfig | None = None,
        token_cache: TokenCache | None = None,
        auth: httpx.Auth | None = None,
        refresh_token_lifetime: int | None = None,
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
            auth.refresh_token_lifetime = refresh_token_lifetime
        self._client = transport_mod.create_http_client(
            base_url=base_url,
            auth=auth,
            http_config=config,
        )
        self._auth = auth
        self._operators = OperatorService(self._client)
        self._tags = TagService(self._client)
        self._component_types = ComponentTypeService(self._client)
        self._component_type_search = ComponentTypeSearchService(self._client)
        self._components = ComponentService(self._client)
        self._component_search = ComponentSearchService(self._client)
        self._policies = PolicyService(self._client)
        self._policy_search = PolicySearchService(self._client)
        self._audit_logs = EntityAuditLogService(self._client)
        self._system_config = SystemConfigService(self._client)
        self._reports = PolicyActivityReportService(self._client)
        self._activity_logs = ReportActivityLogService(self._client)
        self._dashboard = DashboardService(self._client)
        self._reporter_audit_logs = ReporterAuditLogService(self._client)

    @property
    def operators(self) -> OperatorService:
        return self._operators

    @property
    def tags(self) -> TagService:
        return self._tags

    @property
    def component_types(self) -> ComponentTypeService:
        return self._component_types

    @property
    def component_type_search(self) -> ComponentTypeSearchService:
        return self._component_type_search

    @property
    def components(self) -> ComponentService:
        return self._components

    @property
    def component_search(self) -> ComponentSearchService:
        return self._component_search

    @property
    def policies(self) -> PolicyService:
        return self._policies

    @property
    def policy_search(self) -> PolicySearchService:
        return self._policy_search

    @property
    def audit_logs(self) -> EntityAuditLogService:
        return self._audit_logs

    @property
    def system_config(self) -> SystemConfigService:
        return self._system_config

    @property
    def reports(self) -> PolicyActivityReportService:
        return self._reports

    @property
    def activity_logs(self) -> ReportActivityLogService:
        return self._activity_logs

    @property
    def dashboard(self) -> DashboardService:
        return self._dashboard

    @property
    def reporter_audit_logs(self) -> ReporterAuditLogService:
        return self._reporter_audit_logs

    def close(self) -> None:
        self._client.close()

    def authenticate(self) -> None:
        """Acquire and cache a token without issuing any API call.

        Triggers the OIDC password (or refresh) grant via the CloudAz auth
        handler if no valid cached token is available. Safe to call more
        than once; no-op when a valid token is already loaded.

        Raises:
            AuthenticationError: if the configured auth handler does not
                support direct token acquisition (e.g. a custom
                ``auth=`` override) or if the token endpoint rejects the
                credentials.
        """
        if not isinstance(self._auth, CloudAzAuth):
            raise AuthenticationError(
                "authenticate() requires the default CloudAzAuth handler; "
                "a custom auth= override does not support direct token "
                "acquisition.",
                status_code=None,
                response_body=None,
                request_method=None,
                request_url=None,
            )
        self._auth.ensure_token(self._send_unauthenticated)

    def __enter__(self) -> CloudAzClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def _send_unauthenticated(self, request: httpx.Request) -> httpx.Response:
        return self._client.send(request, auth=None)
