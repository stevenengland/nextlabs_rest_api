from __future__ import annotations

import click
import pytest

from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk.exceptions import (
    AuthenticationError,
    NotFoundError,
    ServerError,
)


def test_handler_catches_authentication_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    @cli_error_handler
    def failing() -> None:
        raise AuthenticationError(message="bad creds")

    with pytest.raises(click.exceptions.Exit) as exc_info:
        failing()

    assert exc_info.value.exit_code == 1
    captured = capsys.readouterr()
    assert "Authentication failed" in captured.out


def test_handler_catches_not_found_error(capsys: pytest.CaptureFixture[str]) -> None:
    @cli_error_handler
    def failing() -> None:
        raise NotFoundError(message="HTTP 404")

    with pytest.raises(click.exceptions.Exit) as exc_info:
        failing()

    assert exc_info.value.exit_code == 1
    captured = capsys.readouterr()
    assert "Not found" in captured.out


def test_handler_catches_generic_nextlabs_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    @cli_error_handler
    def failing() -> None:
        raise ServerError(message="HTTP 500")

    with pytest.raises(click.exceptions.Exit) as exc_info:
        failing()

    assert exc_info.value.exit_code == 1
    captured = capsys.readouterr()
    assert "API error" in captured.out


def test_handler_lets_non_sdk_exceptions_propagate() -> None:
    @cli_error_handler
    def failing() -> None:
        msg = "unrelated"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="unrelated"):
        failing()


def test_handler_returns_value_on_success() -> None:
    @cli_error_handler
    def succeeding() -> str:
        return "ok"

    assert succeeding() == "ok"
