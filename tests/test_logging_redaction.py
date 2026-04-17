from __future__ import annotations

import json

from nextlabs_sdk._logging import (
    format_request_line,
    format_response_line,
    redact_body,
    redact_headers,
    truncate,
)
import httpx


def test_authorization_bearer_header_is_redacted() -> None:
    result = redact_headers({"Authorization": "Bearer abcdef123"})

    assert result["Authorization"] == "Bearer ***"


def test_non_bearer_authorization_fully_redacted() -> None:
    result = redact_headers({"Authorization": "Basic xyz"})

    assert result["Authorization"] == "***"


def test_cookie_and_proxy_auth_redacted_case_insensitive() -> None:
    result = redact_headers({"COOKIE": "session=abc", "Proxy-Authorization": "x"})

    assert result["COOKIE"] == "***"
    assert result["Proxy-Authorization"] == "***"


def test_other_headers_preserved() -> None:
    result = redact_headers({"Content-Type": "application/json", "X-Req": "42"})

    assert result == {"Content-Type": "application/json", "X-Req": "42"}


def test_form_body_password_redacted_other_fields_kept() -> None:
    body = b"grant_type=password&username=u&password=secret&client_id=app"

    out = redact_body("application/x-www-form-urlencoded", body)

    assert "password=%2A%2A%2A" in out or "password=***" in out
    assert "username=u" in out
    assert "client_id=app" in out
    assert "secret" not in out


def test_json_body_nested_client_secret_redacted() -> None:
    body = json.dumps({"client_secret": "shh", "nested": {"password": "p"}}).encode()

    out = redact_body("application/json; charset=utf-8", body)

    parsed = json.loads(out)
    assert parsed["client_secret"] == "***"
    assert parsed["nested"]["password"] == "***"


def test_json_array_redacted() -> None:
    body = json.dumps([{"access_token": "a"}, {"id_token": "b"}]).encode()

    out = redact_body("application/json", body)

    parsed = json.loads(out)
    assert parsed[0]["access_token"] == "***"
    assert parsed[1]["id_token"] == "***"


def test_binary_body_is_placeholder() -> None:
    body = b"\xff\xfe\x00\x01"

    out = redact_body("application/octet-stream", body)

    assert out.startswith("<binary,")


def test_empty_body_placeholder() -> None:
    assert redact_body("application/json", b"") == "<empty>"


def test_unknown_content_type_returns_text() -> None:
    out = redact_body("text/plain", b"hello world")

    assert out == "hello world"


def test_invalid_json_falls_back_to_raw_text() -> None:
    out = redact_body("application/json", b"not-json{")

    assert out == "not-json{"


def test_truncate_under_limit_unchanged() -> None:
    assert truncate("short", limit=10) == "short"


def test_truncate_over_limit_annotated() -> None:
    out = truncate("a" * 50, limit=10)

    assert out.startswith("a" * 10)
    assert "truncated" in out
    assert "50 bytes total" in out


def test_format_request_line() -> None:
    request = httpx.Request("POST", "https://example.com/x")

    assert format_request_line(request) == "→ POST https://example.com/x"


def test_format_response_line() -> None:
    request = httpx.Request("GET", "https://example.com/x")
    response = httpx.Response(500, request=request, content=b"hello")

    line = format_response_line(response, elapsed_s=0.123)

    assert line.startswith("← 500")
    assert "(5 bytes)" in line
    assert "0.123s" in line
