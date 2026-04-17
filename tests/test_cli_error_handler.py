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


@pytest.mark.parametrize(
    "exc,expected_substrings",
    [
        pytest.param(
            AuthenticationError(message="bad creds"),
            ["Authentication failed"],
            id="authentication-error",
        ),
        pytest.param(
            NotFoundError(message="HTTP 404"),
            ["Not found"],
            id="not-found-error",
        ),
        pytest.param(
            ServerError(message="HTTP 500"),
            ["API error"],
            id="generic-nextlabs-error",
        ),
        pytest.param(
            TransportError(message="SSL certificate verification failed: ..."),
            ["Connection error", "SSL certificate verification failed"],
            id="transport-error",
        ),
        pytest.param(
            RequestTimeoutError(message="Request timed out: read timed out"),
            ["Request timed out"],
            id="request-timeout-error",
        ),
        pytest.param(
            RuntimeError("unrelated"),
            ["Unexpected error", "unrelated"],
            id="unexpected-exception",
        ),
    ],
)
def test_handler_catches_exception(
    capsys: pytest.CaptureFixture[str],
    exc: Exception,
    expected_substrings: list[str],
):
    @cli_error_handler
    def failing():
        raise exc

    with pytest.raises(click.exceptions.Exit) as exc_info:
        failing()

    assert exc_info.value.exit_code == 1
    captured = capsys.readouterr()
    for substring in expected_substrings:
        assert substring in captured.out


def test_handler_lets_typer_exit_propagate():
    @cli_error_handler
    def failing():
        import typer

        raise typer.Exit(code=2)

    with pytest.raises(click.exceptions.Exit) as exc_info:
        failing()

    assert exc_info.value.exit_code == 2


def test_handler_returns_value_on_success():
    @cli_error_handler
    def succeeding() -> str:
        return "ok"

    assert succeeding() == "ok"
