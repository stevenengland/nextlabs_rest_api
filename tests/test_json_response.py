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


def test_decode_json_message_includes_status_and_content_type() -> None:
    response = _make_response(
        500,
        content=b"boom",
        content_type="text/plain",
    )
    with pytest.raises(ApiError) as exc_info:
        decode_json(response)
    msg = exc_info.value.message
    assert "HTTP 500" in msg
    assert "Content-Type=text/plain" in msg


def test_decode_json_message_reports_missing_content_type_as_unknown() -> None:
    request = httpx.Request("GET", "https://example.com/x")
    response = httpx.Response(200, content=b"nope", request=request)
    assert "content-type" not in response.headers
    with pytest.raises(ApiError) as exc_info:
        decode_json(response)
    assert "Content-Type=unknown" in exc_info.value.message


def test_decode_json_message_includes_redirect_chain() -> None:
    original = httpx.Request("GET", "https://example.com/redirect")
    final = httpx.Request("GET", "https://example.com/final")
    history_response = httpx.Response(
        302,
        headers={"location": "https://example.com/final"},
        request=original,
    )
    response = httpx.Response(
        200,
        content=b"<html>login</html>",
        headers={"content-type": "text/html;charset=utf-8"},
        request=final,
        history=[history_response],
    )
    with pytest.raises(ApiError) as exc_info:
        decode_json(response)
    msg = exc_info.value.message
    assert "HTTP 200" in msg
    assert "Content-Type=text/html;charset=utf-8" in msg
    assert "after 1 redirect" in msg
    assert "https://example.com/redirect" in msg
    assert "https://example.com/final" in msg


def test_decode_json_message_pluralises_multiple_redirects() -> None:
    first_req = httpx.Request("GET", "https://example.com/a")
    second_req = httpx.Request("GET", "https://example.com/b")
    final_req = httpx.Request("GET", "https://example.com/c")
    history = [
        httpx.Response(302, headers={"location": "/b"}, request=first_req),
        httpx.Response(302, headers={"location": "/c"}, request=second_req),
    ]
    response = httpx.Response(
        200,
        content=b"not json",
        headers={"content-type": "text/html"},
        request=final_req,
        history=history,
    )
    with pytest.raises(ApiError) as exc_info:
        decode_json(response)
    assert "after 2 redirects" in exc_info.value.message


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
