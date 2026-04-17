from __future__ import annotations

import click
import pytest

from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk.exceptions import (
    AuthenticationError,
    NotFoundError,
    RequestTimeoutError,
    ServerError,
    TransportError,
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


def test_handler_catches_unexpected_exception_minimally(
    capsys: pytest.CaptureFixture[str],
) -> None:
    @cli_error_handler
    def failing() -> None:
        msg = "unrelated"
        raise RuntimeError(msg)

    with pytest.raises(click.exceptions.Exit) as exc_info:
        failing()

    assert exc_info.value.exit_code == 1
    captured = capsys.readouterr()
    assert "Unexpected error" in captured.out
    assert "unrelated" in captured.out


def test_handler_catches_transport_error_with_connection_prefix(
    capsys: pytest.CaptureFixture[str],
) -> None:
    @cli_error_handler
    def failing() -> None:
        raise TransportError(message="SSL certificate verification failed: ...")

    with pytest.raises(click.exceptions.Exit):
        failing()

    captured = capsys.readouterr()
    assert "Connection error" in captured.out
    assert "SSL certificate verification failed" in captured.out


def test_handler_catches_request_timeout_error_with_timeout_prefix(
    capsys: pytest.CaptureFixture[str],
) -> None:
    @cli_error_handler
    def failing() -> None:
        raise RequestTimeoutError(message="Request timed out: read timed out")

    with pytest.raises(click.exceptions.Exit):
        failing()

    captured = capsys.readouterr()
    assert "Request timed out" in captured.out


def test_handler_lets_typer_exit_propagate() -> None:
    @cli_error_handler
    def failing() -> None:
        import typer

        raise typer.Exit(code=2)

    with pytest.raises(click.exceptions.Exit) as exc_info:
        failing()

    assert exc_info.value.exit_code == 2


def test_handler_returns_value_on_success() -> None:
    @cli_error_handler
    def succeeding() -> str:
        return "ok"

    assert succeeding() == "ok"
