from __future__ import annotations

import pytest

import httpx

from nextlabs_sdk import exceptions


def test_base_exception_carries_context() -> None:
    exc = exceptions.NextLabsError(
        "test error",
        status_code=500,
        response_body="body",
        request_method="GET",
        request_url="https://example.com",
    )
    assert exc.message == "test error"
    assert exc.status_code == 500
    assert exc.response_body == "body"
    assert exc.request_method == "GET"
    assert exc.request_url == "https://example.com"
    assert str(exc) == "test error"


def test_base_exception_defaults_to_none() -> None:
    exc = exceptions.NextLabsError("error")
    assert exc.status_code is None
    assert exc.response_body is None
    assert exc.request_method is None
    assert exc.request_url is None


def test_authentication_error_is_nextlabs_error() -> None:
    assert issubclass(
        exceptions.AuthenticationError,
        exceptions.NextLabsError,
    )


def test_authorization_error_is_nextlabs_error() -> None:
    assert issubclass(
        exceptions.AuthorizationError,
        exceptions.NextLabsError,
    )


def test_not_found_error_is_nextlabs_error() -> None:
    assert issubclass(exceptions.NotFoundError, exceptions.NextLabsError)


def test_validation_error_is_nextlabs_error() -> None:
    assert issubclass(exceptions.ValidationError, exceptions.NextLabsError)


def test_conflict_error_is_nextlabs_error() -> None:
    assert issubclass(exceptions.ConflictError, exceptions.NextLabsError)


def test_server_error_is_nextlabs_error() -> None:
    assert issubclass(exceptions.ServerError, exceptions.NextLabsError)


def test_request_timeout_error_is_nextlabs_error() -> None:
    assert issubclass(
        exceptions.RequestTimeoutError,
        exceptions.NextLabsError,
    )


def test_transport_error_is_nextlabs_error() -> None:
    assert issubclass(exceptions.TransportError, exceptions.NextLabsError)


def test_api_error_is_nextlabs_error() -> None:
    assert issubclass(exceptions.ApiError, exceptions.NextLabsError)


def test_rate_limit_error_is_api_error() -> None:
    assert issubclass(exceptions.RateLimitError, exceptions.ApiError)
    assert issubclass(exceptions.RateLimitError, exceptions.NextLabsError)


def test_subclass_inherits_context_fields() -> None:
    exc = exceptions.AuthenticationError(
        "auth failed",
        status_code=401,
        response_body="Unauthorized",
        request_method="POST",
        request_url="https://example.com/token",
    )
    assert exc.status_code == 401
    assert exc.response_body == "Unauthorized"


def test_raise_for_status_success_does_not_raise() -> None:
    response = httpx.Response(
        200,
        request=httpx.Request("GET", "https://example.com"),
    )
    exceptions.raise_for_status(response)


def test_raise_for_status_301_does_not_raise() -> None:
    response = httpx.Response(
        301,
        request=httpx.Request("GET", "https://example.com"),
    )
    exceptions.raise_for_status(response)


def test_raise_for_status_400_raises_validation_error() -> None:
    response = httpx.Response(
        400,
        text="bad request",
        request=httpx.Request("POST", "https://example.com/api"),
    )
    with pytest.raises(exceptions.ValidationError) as exc_info:
        exceptions.raise_for_status(response)
    assert exc_info.value.status_code == 400
    assert exc_info.value.response_body == "bad request"
    assert exc_info.value.request_method == "POST"
    assert exc_info.value.request_url == "https://example.com/api"


def test_raise_for_status_401_raises_authentication_error() -> None:
    response = httpx.Response(
        401,
        request=httpx.Request("GET", "https://example.com"),
    )
    with pytest.raises(exceptions.AuthenticationError):
        exceptions.raise_for_status(response)


def test_raise_for_status_403_raises_authorization_error() -> None:
    response = httpx.Response(
        403,
        request=httpx.Request("GET", "https://example.com"),
    )
    with pytest.raises(exceptions.AuthorizationError):
        exceptions.raise_for_status(response)


def test_raise_for_status_404_raises_not_found_error() -> None:
    response = httpx.Response(
        404,
        request=httpx.Request("GET", "https://example.com"),
    )
    with pytest.raises(exceptions.NotFoundError):
        exceptions.raise_for_status(response)


def test_raise_for_status_409_raises_conflict_error() -> None:
    response = httpx.Response(
        409,
        request=httpx.Request("GET", "https://example.com"),
    )
    with pytest.raises(exceptions.ConflictError):
        exceptions.raise_for_status(response)


def test_raise_for_status_429_raises_rate_limit_error() -> None:
    response = httpx.Response(
        429,
        request=httpx.Request("GET", "https://example.com"),
    )
    with pytest.raises(exceptions.RateLimitError):
        exceptions.raise_for_status(response)


def test_raise_for_status_500_raises_server_error() -> None:
    response = httpx.Response(
        500,
        request=httpx.Request("GET", "https://example.com"),
    )
    with pytest.raises(exceptions.ServerError):
        exceptions.raise_for_status(response)


def test_raise_for_status_502_raises_server_error() -> None:
    response = httpx.Response(
        502,
        request=httpx.Request("GET", "https://example.com"),
    )
    with pytest.raises(exceptions.ServerError):
        exceptions.raise_for_status(response)


def test_raise_for_status_422_raises_api_error() -> None:
    response = httpx.Response(
        422,
        request=httpx.Request("GET", "https://example.com"),
    )
    with pytest.raises(exceptions.ApiError):
        exceptions.raise_for_status(response)
