from __future__ import annotations

import logging

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


class TestEnvelopeDebugLogging:
    """Each (None, None) path emits a distinct debug-level reason (issue #96)."""

    def _reasons(self, caplog: pytest.LogCaptureFixture) -> list[str | None]:
        return [
            record.__dict__.get("reason")
            for record in caplog.records
            if record.name == "nextlabs_sdk" and record.levelno == logging.DEBUG
        ]

    def test_logs_body_not_json(self, caplog: pytest.LogCaptureFixture):
        response = httpx.Response(500, text="<html>not json</html>")
        with caplog.at_level(logging.DEBUG, logger="nextlabs_sdk"):
            envelope_from_response(response)
        assert "body_not_json" in self._reasons(caplog)

    def test_logs_body_not_mapping(self, caplog: pytest.LogCaptureFixture):
        with caplog.at_level(logging.DEBUG, logger="nextlabs_sdk"):
            envelope_from_mapping(["statusCode", "6000"])
        assert "body_not_mapping" in self._reasons(caplog)

    def test_logs_missing_status_code(self, caplog: pytest.LogCaptureFixture):
        with caplog.at_level(logging.DEBUG, logger="nextlabs_sdk"):
            envelope_from_mapping({"message": "no code"})
        assert "missing_status_code" in self._reasons(caplog)

    def test_logs_status_code_not_string(self, caplog: pytest.LogCaptureFixture):
        with caplog.at_level(logging.DEBUG, logger="nextlabs_sdk"):
            envelope_from_mapping({"statusCode": 1003, "message": "m"})
        assert "status_code_not_string" in self._reasons(caplog)

    def test_success_path_does_not_log(self, caplog: pytest.LogCaptureFixture):
        with caplog.at_level(logging.DEBUG, logger="nextlabs_sdk"):
            envelope_from_mapping({"statusCode": "6000", "message": "boom"})
        assert self._reasons(caplog) == []
