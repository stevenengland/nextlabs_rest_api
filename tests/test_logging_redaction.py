from __future__ import annotations

import json

import httpx
import pytest

from nextlabs_sdk._logging import (
    format_request_line,
    format_response_line,
    redact_body,
    redact_headers,
    truncate,
)


@pytest.mark.parametrize(
    "headers,expected",
    [
        pytest.param(
            {"Authorization": "Bearer abcdef123"},
            {"Authorization": "Bearer ***"},
            id="bearer-token",
        ),
        pytest.param(
            {"Authorization": "Basic xyz"},
            {"Authorization": "***"},
            id="non-bearer-auth",
        ),
        pytest.param(
            {"COOKIE": "session=abc", "Proxy-Authorization": "x"},
            {"COOKIE": "***", "Proxy-Authorization": "***"},
            id="cookie-and-proxy-auth",
        ),
        pytest.param(
            {"Content-Type": "application/json", "X-Req": "42"},
            {"Content-Type": "application/json", "X-Req": "42"},
            id="other-headers-preserved",
        ),
    ],
)
def test_redact_headers(headers, expected):
    result = redact_headers(headers)
    for key, value in expected.items():
        assert result[key] == value


def test_form_body_password_redacted_other_fields_kept():
    body = b"grant_type=password&username=u&password=secret&client_id=app"

    out = redact_body("application/x-www-form-urlencoded", body)

    assert "password=%2A%2A%2A" in out or "password=***" in out
    assert "username=u" in out
    assert "client_id=app" in out
    assert "secret" not in out


@pytest.mark.parametrize(
    "payload,content_type,checks",
    [
        pytest.param(
            {"client_secret": "shh", "nested": {"password": "p"}},
            "application/json; charset=utf-8",
            [("client_secret", "***"), (("nested", "password"), "***")],
            id="nested-client-secret",
        ),
        pytest.param(
            [{"access_token": "a"}, {"id_token": "b"}],
            "application/json",
            [((0, "access_token"), "***"), ((1, "id_token"), "***")],
            id="json-array",
        ),
    ],
)
def test_json_body_redacted(payload, content_type, checks):
    body = json.dumps(payload).encode()

    out = redact_body(content_type, body)
    parsed = json.loads(out)
    for path, expected in checks:
        node = parsed
        if isinstance(path, tuple):
            for key in path:
                node = node[key]
        else:
            node = node[path]
        assert node == expected


@pytest.mark.parametrize(
    "content_type,body,expected",
    [
        pytest.param(
            "application/octet-stream",
            b"\xff\xfe\x00\x01",
            "<binary,",
            id="binary-prefix",
        ),
        pytest.param("application/json", b"", "<empty>", id="empty-body"),
        pytest.param(
            "text/plain", b"hello world", "hello world", id="unknown-content-type"
        ),
        pytest.param(
            "application/json", b"not-json{", "not-json{", id="invalid-json-fallback"
        ),
    ],
)
def test_redact_body_variants(content_type, body, expected):
    out = redact_body(content_type, body)
    if expected == "<binary,":
        assert out.startswith(expected)
    else:
        assert out == expected


def test_truncate_under_limit_unchanged():
    assert truncate("short", limit=10) == "short"


def test_truncate_over_limit_annotated():
    out = truncate("a" * 50, limit=10)

    assert out.startswith("a" * 10)
    assert "truncated" in out
    assert "50 bytes total" in out


def test_format_request_line():
    request = httpx.Request("POST", "https://example.com/x")

    assert format_request_line(request) == "→ POST https://example.com/x"


def test_format_response_line():
    request = httpx.Request("GET", "https://example.com/x")
    response = httpx.Response(500, request=request, content=b"hello")

    line = format_response_line(response, elapsed_s=0.123)

    assert line.startswith("← 500")
    assert "(5 bytes)" in line
    assert "0.123s" in line
