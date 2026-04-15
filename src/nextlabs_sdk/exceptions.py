from __future__ import annotations

from types import MappingProxyType

import httpx

_CLIENT_ERROR_THRESHOLD = 400
_SERVER_ERROR_THRESHOLD = 500


class NextLabsError(Exception):

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
        request_method: str | None = None,
        request_url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        self.request_method = request_method
        self.request_url = request_url


class AuthenticationError(NextLabsError):
    """HTTP 401 or token acquisition failure."""


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

    error_class = _STATUS_CODE_MAP.get(status_code)
    if error_class is not None:
        raise error_class(
            message=f"HTTP {status_code}",
            status_code=status_code,
            response_body=response_body,
            request_method=request_method,
            request_url=request_url,
        )

    if status_code >= _SERVER_ERROR_THRESHOLD:
        raise ServerError(
            message=f"HTTP {status_code}",
            status_code=status_code,
            response_body=response_body,
            request_method=request_method,
            request_url=request_url,
        )

    raise ApiError(
        message=f"HTTP {status_code}",
        status_code=status_code,
        response_body=response_body,
        request_method=request_method,
        request_url=request_url,
    )
