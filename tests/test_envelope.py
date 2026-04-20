from __future__ import annotations

import httpx
import pytest

from nextlabs_sdk._envelope import envelope_from_mapping, envelope_from_response


def _response(body: object | str | None, *, status: int = 200) -> httpx.Response:
    if isinstance(body, str):
        return httpx.Response(status, text=body)
    if body is None:
        return httpx.Response(status)
    return httpx.Response(status, json=body)


def test_returns_statuscode_and_message_for_envelope():
    response = _response({"statusCode": "6000", "message": "boom"}, status=400)
    assert envelope_from_response(response) == ("6000", "boom")


def test_returns_only_statuscode_when_message_missing():
    response = _response({"statusCode": "5000"}, status=200)
    assert envelope_from_response(response) == ("5000", None)


def test_returns_only_statuscode_when_message_empty_string():
    response = _response({"statusCode": "5000", "message": ""}, status=200)
    assert envelope_from_response(response) == ("5000", None)


def test_returns_only_statuscode_when_message_not_string():
    response = _response({"statusCode": "5000", "message": 123}, status=200)
    assert envelope_from_response(response) == ("5000", None)


def test_returns_none_when_statuscode_missing():
    response = _response({"message": "no statusCode here"}, status=200)
    assert envelope_from_response(response) == (None, None)


def test_returns_none_when_statuscode_not_string():
    response = _response({"statusCode": 1003, "message": "ok"}, status=200)
    assert envelope_from_response(response) == (None, None)


def test_returns_none_when_body_is_not_object():
    response = _response(["statusCode", "6000"], status=400)
    assert envelope_from_response(response) == (None, None)


def test_returns_none_when_body_is_malformed_json():
    response = _response("<html>not json</html>", status=500)
    assert envelope_from_response(response) == (None, None)


def test_returns_none_when_body_is_empty():
    response = _response("", status=500)
    assert envelope_from_response(response) == (None, None)


@pytest.mark.parametrize("code", ["1003", "5000", "6000"])
def test_success_and_error_codes_pass_through_unchanged(code: str):
    response = _response({"statusCode": code, "message": "m"}, status=200)
    assert envelope_from_response(response) == (code, "m")


class TestEnvelopeFromMapping:
    def test_extracts_statuscode_and_message(self):
        assert envelope_from_mapping({"statusCode": "6000", "message": "boom"}) == (
            "6000",
            "boom",
        )

    def test_returns_none_none_for_non_mapping(self):
        assert envelope_from_mapping(["statusCode", "6000"]) == (None, None)
        assert envelope_from_mapping("statusCode=6000") == (None, None)
        assert envelope_from_mapping(None) == (None, None)
        assert envelope_from_mapping(42) == (None, None)

    def test_empty_string_message_normalized_to_none(self):
        assert envelope_from_mapping({"statusCode": "5000", "message": ""}) == (
            "5000",
            None,
        )

    def test_non_string_statuscode_rejected(self):
        assert envelope_from_mapping({"statusCode": 1003, "message": "m"}) == (
            None,
            None,
        )
