from __future__ import annotations

import httpx
import pytest

from nextlabs_sdk._json_response import decode_json, require_key
from nextlabs_sdk.exceptions import ApiError, AuthenticationError


def _make_response(
    status_code: int,
    *,
    content: bytes = b"",
    content_type: str = "application/json",
) -> httpx.Response:
    request = httpx.Request("POST", "https://example.com/cas/oidc/accessToken")
    return httpx.Response(
        status_code,
        content=content,
        headers={"content-type": content_type},
        request=request,
    )


def test_decode_json_returns_body_on_valid_json() -> None:
    response = _make_response(200, content=b'{"a": 1}')
    assert decode_json(response) == {"a": 1}


def test_decode_json_raises_api_error_on_invalid_json() -> None:
    response = _make_response(200, content=b"<html>oops</html>")
    with pytest.raises(ApiError) as exc_info:
        decode_json(response)
    assert "Invalid JSON response" in exc_info.value.message
    assert exc_info.value.status_code == 200
    assert exc_info.value.request_method == "POST"
    assert exc_info.value.request_url == ("https://example.com/cas/oidc/accessToken")


def test_decode_json_respects_custom_error_class() -> None:
    response = _make_response(200, content=b"nope")
    with pytest.raises(AuthenticationError):
        decode_json(response, error_cls=AuthenticationError)


def test_decode_json_truncates_long_bodies() -> None:
    big = b"x" * 2000
    response = _make_response(200, content=big)
    with pytest.raises(ApiError) as exc_info:
        decode_json(response)
    body = exc_info.value.response_body or ""
    assert len(body) < 600
    assert body.endswith("… (truncated)")


def test_require_key_returns_value_when_present() -> None:
    assert require_key({"foo": 42}, "foo") == 42


def test_require_key_raises_api_error_when_missing() -> None:
    with pytest.raises(ApiError) as exc_info:
        require_key({"foo": 1}, "bar", context=" in envelope")
    assert "missing 'bar' in envelope" in exc_info.value.message


def test_require_key_respects_custom_error_class() -> None:
    with pytest.raises(AuthenticationError):
        require_key({}, "id_token", error_cls=AuthenticationError)
