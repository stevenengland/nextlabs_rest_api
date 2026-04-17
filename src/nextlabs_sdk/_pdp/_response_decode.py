from __future__ import annotations

from typing import Callable, TypeVar

import httpx

from nextlabs_sdk._json_response import decode_json
from nextlabs_sdk.exceptions import ApiError

T_Payload = TypeVar("T_Payload")


def decode_pdp_response(
    response: httpx.Response,
    deserializer: Callable[[dict[str, object]], T_Payload],
    *,
    what: str,
) -> T_Payload:
    """Decode a PDP JSON response and run the deserializer with guardrails."""
    body = decode_json(response)
    if not isinstance(body, dict):
        raise ApiError(
            f"Unexpected PDP response shape while decoding {what}: expected object",
            status_code=response.status_code,
        )
    try:
        return deserializer(body)
    except (KeyError, TypeError, ValueError) as exc:
        raise ApiError(
            f"Unexpected PDP response shape while decoding {what}: {exc}",
            status_code=response.status_code,
        ) from exc
