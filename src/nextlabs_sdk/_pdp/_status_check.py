from __future__ import annotations

import httpx

from nextlabs_sdk.exceptions import PdpStatusError

XACML_STATUS_OK = "urn:oasis:names:tc:xacml:1.0:status:ok"

_BODY_PREVIEW_LIMIT = 4096


def raise_if_not_ok(
    response: httpx.Response,
    *,
    code: str,
    message: str,
) -> None:
    """Raise ``PdpStatusError`` when ``code`` is set and not the ok URN.

    Empty or missing codes are treated as ok; only an explicit non-ok
    XACML status code triggers the exception.
    """
    if not code or code == XACML_STATUS_OK:
        return
    friendly = message or f"PDP returned status {code}"
    request = response.request
    raise PdpStatusError(
        friendly,
        xacml_status_code=code,
        xacml_status_message=message,
        status_code=response.status_code,
        response_body=_body_preview(response),
        request_method=request.method,
        request_url=str(request.url),
    )


def _body_preview(response: httpx.Response) -> str:
    text = response.text
    if len(text) > _BODY_PREVIEW_LIMIT:
        return text[:_BODY_PREVIEW_LIMIT]
    return text
