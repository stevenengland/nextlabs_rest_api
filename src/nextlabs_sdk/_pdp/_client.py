from __future__ import annotations

from types import TracebackType

from nextlabs_sdk import _http_transport as transport_mod
from nextlabs_sdk._auth._pdp_auth import PdpAuth
from nextlabs_sdk._config import HttpConfig
from nextlabs_sdk._pdp import _json_serializer as json_ser
from nextlabs_sdk._pdp import _xml_serializer as xml_ser
from nextlabs_sdk._pdp._enums import ContentType
from nextlabs_sdk._pdp._request_models import EvalRequest, PermissionsRequest
from nextlabs_sdk._pdp._response_decode import decode_pdp_response
from nextlabs_sdk._pdp._response_models import EvalResponse, PermissionsResponse
from nextlabs_sdk.exceptions import raise_for_status

_PDP_ENDPOINT = "/dpc/authorization/pdp"
_CONTENT_TYPE = "Content-Type"


class PdpClient:
    """Synchronous client for the NextLabs PDP REST API."""

    def __init__(
        self,
        *,
        base_url: str,
        client_id: str,
        client_secret: str,
        token_url: str | None = None,
        http_config: HttpConfig | None = None,
    ) -> None:
        config = http_config or HttpConfig()
        effective_token_url = token_url or f"{base_url}/cas/token"
        auth = PdpAuth(
            token_url=effective_token_url,
            client_id=client_id,
            client_secret=client_secret,
        )
        self._client = transport_mod.create_http_client(
            base_url=base_url,
            auth=auth,
            http_config=config,
        )

    def evaluate(
        self,
        request: EvalRequest,
        *,
        content_type: ContentType = ContentType.JSON,
    ) -> EvalResponse:
        if content_type == ContentType.XML:
            body_bytes = xml_ser.serialize_eval_request(request)
            response = self._client.post(
                _PDP_ENDPOINT,
                content=body_bytes,
                headers={_CONTENT_TYPE: content_type.value},
            )
            raise_for_status(response)
            return xml_ser.deserialize_eval_response(response.content)

        body = json_ser.serialize_eval_request(request)
        response = self._client.post(
            _PDP_ENDPOINT,
            json=body,
            headers={_CONTENT_TYPE: content_type.value},
        )
        raise_for_status(response)
        return decode_pdp_response(
            response,
            json_ser.deserialize_eval_response,
            what="eval response",
        )

    def permissions(
        self,
        request: PermissionsRequest,
        *,
        content_type: ContentType = ContentType.JSON,
    ) -> PermissionsResponse:
        if content_type == ContentType.XML:
            body_bytes = xml_ser.serialize_permissions_request(request)
            response = self._client.post(
                _PDP_ENDPOINT,
                content=body_bytes,
                headers={_CONTENT_TYPE: content_type.value},
            )
            raise_for_status(response)
            return xml_ser.deserialize_permissions_response(response.content)

        body = json_ser.serialize_permissions_request(request)
        response = self._client.post(
            _PDP_ENDPOINT,
            json=body,
            headers={_CONTENT_TYPE: content_type.value},
        )
        raise_for_status(response)
        return decode_pdp_response(
            response,
            json_ser.deserialize_permissions_response,
            what="permissions response",
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PdpClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
