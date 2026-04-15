from __future__ import annotations

from types import TracebackType

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._auth._cloudaz_auth import CloudAzAuth
from nextlabs_sdk._cloudaz._operators import AsyncOperatorService
from nextlabs_sdk._cloudaz._tags import AsyncTagService
from nextlabs_sdk._config import HttpConfig


class AsyncCloudAzClient:
    """Asynchronous client for the NextLabs CloudAz Console API."""

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
        self._client = transport_mod.create_async_http_client(
            base_url=base_url,
            auth=auth,
            timeout=config.timeout,
            verify_ssl=config.verify_ssl,
            retry=config.retry,
        )
        self._operators = AsyncOperatorService(self._client)
        self._tags = AsyncTagService(self._client)

    @property
    def operators(self) -> AsyncOperatorService:
        return self._operators

    @property
    def tags(self) -> AsyncTagService:
        return self._tags

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
