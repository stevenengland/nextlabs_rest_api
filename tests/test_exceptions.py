from __future__ import annotations

import httpx
import pytest

from nextlabs_sdk import exceptions


def test_base_exception_carries_context():
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


def test_base_exception_defaults_to_none():
    exc = exceptions.NextLabsError("error")
    assert exc.status_code is None
    assert exc.response_body is None
    assert exc.request_method is None
    assert exc.request_url is None


@pytest.mark.parametrize(
    "child,parent",
    [
        pytest.param(
            exceptions.AuthenticationError,
            exceptions.NextLabsError,
            id="authentication",
        ),
        pytest.param(
            exceptions.AuthorizationError, exceptions.NextLabsError, id="authorization"
        ),
        pytest.param(
            exceptions.NotFoundError, exceptions.NextLabsError, id="not-found"
        ),
        pytest.param(
            exceptions.ValidationError, exceptions.NextLabsError, id="validation"
        ),
        pytest.param(exceptions.ConflictError, exceptions.NextLabsError, id="conflict"),
        pytest.param(exceptions.ServerError, exceptions.NextLabsError, id="server"),
        pytest.param(
            exceptions.RequestTimeoutError, exceptions.NextLabsError, id="timeout"
        ),
        pytest.param(
            exceptions.TransportError, exceptions.NextLabsError, id="transport"
        ),
        pytest.param(exceptions.ApiError, exceptions.NextLabsError, id="api"),
        pytest.param(
            exceptions.RateLimitError, exceptions.ApiError, id="rate-limit-is-api"
        ),
        pytest.param(
            exceptions.RateLimitError,
            exceptions.NextLabsError,
            id="rate-limit-is-nextlabs",
        ),
    ],
)
def test_exception_class_is_subclass(child: type, parent: type):
    assert issubclass(child, parent)


def test_subclass_inherits_context_fields():
    exc = exceptions.AuthenticationError(
        "auth failed",
        status_code=401,
        response_body="Unauthorized",
        request_method="POST",
        request_url="https://example.com/token",
    )
    assert exc.status_code == 401
    assert exc.response_body == "Unauthorized"


def _response(
    status: int,
    text: str = "",
    method: str = "GET",
    url: str = "https://example.com",
) -> httpx.Response:
    return httpx.Response(status, text=text, request=httpx.Request(method, url))


@pytest.mark.parametrize(
    "status",
    [
        pytest.param(200, id="200-ok"),
        pytest.param(301, id="301-redirect"),
    ],
)
def test_raise_for_status_success_does_not_raise(status: int):
    exceptions.raise_for_status(_response(status))


@pytest.mark.parametrize(
    "status,exc_type",
    [
        pytest.param(400, exceptions.ValidationError, id="400-validation"),
        pytest.param(401, exceptions.AuthenticationError, id="401-authentication"),
        pytest.param(403, exceptions.AuthorizationError, id="403-authorization"),
        pytest.param(404, exceptions.NotFoundError, id="404-not-found"),
        pytest.param(409, exceptions.ConflictError, id="409-conflict"),
        pytest.param(422, exceptions.ApiError, id="422-api"),
        pytest.param(429, exceptions.RateLimitError, id="429-rate-limit"),
        pytest.param(500, exceptions.ServerError, id="500-server"),
        pytest.param(502, exceptions.ServerError, id="502-server"),
    ],
)
def test_raise_for_status_maps_status_to_exception(status: int, exc_type: type):
    with pytest.raises(exc_type):
        exceptions.raise_for_status(_response(status))


def test_raise_for_status_400_populates_context():
    with pytest.raises(exceptions.ValidationError) as exc_info:
        exceptions.raise_for_status(
            _response(
                400, text="bad request", method="POST", url="https://example.com/api"
            ),
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.response_body == "bad request"
    assert exc_info.value.request_method == "POST"
    assert exc_info.value.request_url == "https://example.com/api"
