from __future__ import annotations

from types import TracebackType

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._auth._cloudaz_auth import CloudAzAuth
from nextlabs_sdk._cloudaz._component_search import ComponentSearchService
from nextlabs_sdk._cloudaz._component_type_search import ComponentTypeSearchService
from nextlabs_sdk._cloudaz._component_types import ComponentTypeService
from nextlabs_sdk._cloudaz._components import ComponentService
from nextlabs_sdk._cloudaz._operators import OperatorService
from nextlabs_sdk._cloudaz._tags import TagService
from nextlabs_sdk._config import HttpConfig


class CloudAzClient:
    """Synchronous client for the NextLabs CloudAz Console API."""

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        client_id: str = "ControlCenterOIDCClient",
        http_config: HttpConfig | None = None,
    ) -> None:
        config = http_config or HttpConfig()
        auth = CloudAzAuth(
            token_url=f"{base_url}/cas/oidc/accessToken",
            username=username,
            password=password,
            client_id=client_id,
        )
        self._client = transport_mod.create_http_client(
            base_url=base_url,
            auth=auth,
            timeout=config.timeout,
            verify_ssl=config.verify_ssl,
            retry=config.retry,
        )
        self._operators = OperatorService(self._client)
        self._tags = TagService(self._client)
        self._component_types = ComponentTypeService(self._client)
        self._component_type_search = ComponentTypeSearchService(self._client)
        self._components = ComponentService(self._client)
        self._component_search = ComponentSearchService(self._client)

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

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CloudAzClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
