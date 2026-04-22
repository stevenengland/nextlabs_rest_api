from __future__ import annotations

from types import TracebackType

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._auth._pdp_auth import PdpAuth
from nextlabs_sdk._config import HttpConfig
from nextlabs_sdk._pdp import _json_serializer as json_ser
from nextlabs_sdk._pdp import _xml_serializer as xml_ser
from nextlabs_sdk._pdp._enums import ContentType
from nextlabs_sdk._pdp._headers import (
    DEFAULT_SERVICE,
    DEFAULT_VERSION,
    build_pdp_headers,
)
from nextlabs_sdk._pdp._request_models import EvalRequest, PermissionsRequest
from nextlabs_sdk._pdp._response_decode import decode_pdp_response
from nextlabs_sdk._pdp._response_models import EvalResponse, PermissionsResponse
from nextlabs_sdk._pdp._token_url import resolve_pdp_token_url
from nextlabs_sdk.exceptions import NextLabsError, raise_for_status

_PDP_ENDPOINT = "/dpc/authorization/pdp"


def _require_json_content_type(content_type: ContentType, *, method: str) -> None:
    if content_type is not ContentType.JSON:
        raise NextLabsError(
            f"{method}() only supports ContentType.JSON; "
            f"raw XML pass-through is not implemented",
        )


class AsyncPdpClient:
    """Asynchronous client for the NextLabs PDP REST API."""

    def __init__(  # noqa: WPS211
        self,
        *,
        base_url: str,
        client_id: str,
        client_secret: str,
        auth_base_url: str | None = None,
        token_url: str | None = None,
        http_config: HttpConfig | None = None,
        service: str = DEFAULT_SERVICE,
        version: str = DEFAULT_VERSION,
    ) -> None:
        config = http_config or HttpConfig()
        effective_token_url = resolve_pdp_token_url(
            base_url=base_url,
            auth_base_url=auth_base_url,
            token_url=token_url,
        )
        auth = PdpAuth(
            token_url=effective_token_url,
            client_id=client_id,
            client_secret=client_secret,
        )
        self._client = transport_mod.create_async_http_client(
            base_url=base_url,
            auth=auth,
            http_config=config,
        )
        self._service = service
        self._version = version

    async def evaluate(
        self,
        request: EvalRequest,
        *,
        content_type: ContentType = ContentType.JSON,
    ) -> EvalResponse:
        if content_type == ContentType.XML:
            body_bytes = xml_ser.serialize_eval_request(request)
            response = await self._client.post(
                _PDP_ENDPOINT,
                content=body_bytes,
                headers=build_pdp_headers(
                    content_type, service=self._service, version=self._version
                ),
            )
            raise_for_status(response)
            return xml_ser.deserialize_eval_response(response.content)

        body = json_ser.serialize_eval_request(request)
        response = await self._client.post(
            _PDP_ENDPOINT,
            json=body,
            headers=build_pdp_headers(
                content_type, service=self._service, version=self._version
            ),
        )
        raise_for_status(response)
        return decode_pdp_response(
            response,
            json_ser.deserialize_eval_response,
            what="eval response",
        )

    async def permissions(
        self,
        request: PermissionsRequest,
        *,
        content_type: ContentType = ContentType.JSON,
    ) -> PermissionsResponse:
        if content_type == ContentType.XML:
            body_bytes = xml_ser.serialize_permissions_request(request)
            response = await self._client.post(
                _PDP_ENDPOINT,
                content=body_bytes,
                headers=build_pdp_headers(
                    content_type, service=self._service, version=self._version
                ),
            )
            raise_for_status(response)
            return xml_ser.deserialize_permissions_response(response.content)

        body = json_ser.serialize_permissions_request(request)
        response = await self._client.post(
            _PDP_ENDPOINT,
            json=body,
            headers=build_pdp_headers(
                content_type, service=self._service, version=self._version
            ),
        )
        raise_for_status(response)
        return decode_pdp_response(
            response,
            json_ser.deserialize_permissions_response,
            what="permissions response",
        )

    async def evaluate_raw(
        self,
        body: dict[str, object],
        *,
        content_type: ContentType = ContentType.JSON,
    ) -> EvalResponse:
        """POST a pre-built raw XACML JSON body to the PDP eval endpoint."""
        _require_json_content_type(content_type, method="evaluate_raw")
        response = await self._client.post(
            _PDP_ENDPOINT,
            json=body,
            headers=build_pdp_headers(
                content_type, service=self._service, version=self._version
            ),
        )
        raise_for_status(response)
        return decode_pdp_response(
            response,
            json_ser.deserialize_eval_response,
            what="eval response",
        )

    async def permissions_raw(
        self,
        body: dict[str, object],
        *,
        content_type: ContentType = ContentType.JSON,
    ) -> PermissionsResponse:
        """POST a pre-built raw XACML JSON body to the PDP permissions endpoint."""
        _require_json_content_type(content_type, method="permissions_raw")
        response = await self._client.post(
            _PDP_ENDPOINT,
            json=body,
            headers=build_pdp_headers(
                content_type, service=self._service, version=self._version
            ),
        )
        raise_for_status(response)
        return decode_pdp_response(
            response,
            json_ser.deserialize_permissions_response,
            what="permissions response",
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncPdpClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()
