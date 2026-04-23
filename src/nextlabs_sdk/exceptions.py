from __future__ import annotations

from types import MappingProxyType

import httpx

from nextlabs_sdk._envelope import envelope_from_response

_CLIENT_ERROR_THRESHOLD = 400
_SERVER_ERROR_THRESHOLD = 500


class NextLabsError(Exception):  # noqa: WPS230

    def __init__(  # noqa: WPS211
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
        request_method: str | None = None,
        request_url: str | None = None,
        envelope_status_code: str | None = None,
        envelope_message: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        self.request_method = request_method
        self.request_url = request_url
        self.envelope_status_code = envelope_status_code
        self.envelope_message = envelope_message


class AuthenticationError(NextLabsError):
    """HTTP 401 or token acquisition failure."""


class RefreshTokenExpiredError(AuthenticationError):
    """Refresh token is no longer usable.

    Raised either when the SDK determines proactively that the
    configured refresh-token lifetime has elapsed, or when the token
    endpoint rejects a refresh-token grant at runtime and no password
    is available for fallback. Subclasses :class:`AuthenticationError`
    so that existing ``except AuthenticationError:`` handlers continue
    to catch it.
    """


class AuthorizationError(NextLabsError):
    """HTTP 403."""


class NotFoundError(NextLabsError):
    """HTTP 404."""


class ValidationError(NextLabsError):
    """HTTP 400."""


class ConflictError(NextLabsError):
    """HTTP 409."""


class ServerError(NextLabsError):
    """HTTP 5xx after retries exhausted."""


class RequestTimeoutError(NextLabsError):
    """Request timeout after retries exhausted."""


class TransportError(NextLabsError):
    """Transport-level failure after retries exhausted."""


class ApiError(NextLabsError):
    """Catch-all for unmapped HTTP errors."""


class PdpPayloadError(NextLabsError):
    """Raised for invalid or unreadable PDP request payload files."""


class PdpStatusError(ApiError):
    """Raised when the PDP returns a non-ok XACML Status on HTTP 200.

    Inherits from :class:`ApiError` so existing callers that catch
    ``ApiError`` continue to work.
    """

    def __init__(  # noqa: WPS211
        self,
        message: str,
        *,
        xacml_status_code: str,
        xacml_status_message: str = "",
        status_code: int | None = None,
        response_body: str | None = None,
        request_method: str | None = None,
        request_url: str | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            response_body=response_body,
            request_method=request_method,
            request_url=request_url,
            envelope_status_code=xacml_status_code,
            envelope_message=xacml_status_message or message,
        )
        self.xacml_status_code = xacml_status_code
        self.xacml_status_message = xacml_status_message


class RateLimitError(ApiError):
    """HTTP 429 after retries exhausted."""


_STATUS_CODE_MAP = MappingProxyType(
    {
        400: ValidationError,
        401: AuthenticationError,
        403: AuthorizationError,
        404: NotFoundError,
        409: ConflictError,
        429: RateLimitError,
    }
)


def raise_for_status(response: httpx.Response) -> None:
    status_code = response.status_code
    if status_code < _CLIENT_ERROR_THRESHOLD:
        return

    response_body = response.text
    request_method = response.request.method
    request_url = str(response.request.url)

    envelope_status_code, envelope_message = envelope_from_response(response)
    message = envelope_message or f"HTTP {status_code}"

    error_class = _STATUS_CODE_MAP.get(status_code)
    if error_class is None:
        if status_code >= _SERVER_ERROR_THRESHOLD:
            error_class = ServerError
        else:
            error_class = ApiError

    raise error_class(
        message=message,
        status_code=status_code,
        response_body=response_body,
        request_method=request_method,
        request_url=request_url,
        envelope_status_code=envelope_status_code,
        envelope_message=envelope_message,
    )
