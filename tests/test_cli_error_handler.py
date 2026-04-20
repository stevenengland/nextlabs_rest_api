from __future__ import annotations

import click
import pytest
import typer

from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output_format import OutputFormat
from nextlabs_sdk.exceptions import (
    AuthenticationError,
    NotFoundError,
    RefreshTokenExpiredError,
    RequestTimeoutError,
    ServerError,
    TransportError,
)


def _isatty_true() -> bool:
    return True


def _isatty_false() -> bool:
    return False


def _make_cli_ctx(
    *,
    password: str | None = None,
    base_url: str | None = "https://example.com",
    username: str | None = "user",
) -> CliContext:
    return CliContext(
        base_url=base_url,
        username=username,
        password=password,
        client_id="client",
        client_secret=None,
        pdp_url=None,
        output_format=OutputFormat.TABLE,
        verify=None,
        timeout=30.0,
    )


def _make_typer_context(cli_ctx: CliContext) -> typer.Context:
    command = click.Command("test")
    ctx = typer.Context(command)
    ctx.obj = cli_ctx
    return ctx


@pytest.mark.parametrize(
    "exc,expected_substrings",
    [
        pytest.param(
            AuthenticationError(message="bad creds"),
            ["Authentication failed"],
            id="authentication-error",
        ),
        pytest.param(
            RefreshTokenExpiredError(message="refresh rejected"),
            ["Re-login required", "refresh rejected"],
            id="refresh-token-expired",
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


def test_refresh_token_expired_retries_on_tty_after_password_prompt(
    monkeypatch: pytest.MonkeyPatch,
):
    cli_ctx = _make_cli_ctx(password=None)
    ctx = _make_typer_context(cli_ctx)
    prompts: list[tuple[str, bool]] = []

    def _fake_prompt(label: str, *, hide_input: bool = False, **_: object) -> str:
        prompts.append((label, hide_input))
        return "typed-pw"

    monkeypatch.setattr(typer, "prompt", _fake_prompt)
    monkeypatch.setattr("sys.stdin.isatty", _isatty_true)

    calls: list[str | None] = []

    @cli_error_handler
    def command(_ctx: typer.Context) -> str:
        calls.append(_ctx.obj.password)
        if len(calls) == 1:
            raise RefreshTokenExpiredError("refresh rejected")
        return "ok"

    result = command(ctx)

    assert result == "ok"
    assert calls == [None, "typed-pw"]
    assert prompts and prompts[0][1] is True
    assert "user@https://example.com" in prompts[0][0]


def test_refresh_token_expired_reraises_when_not_tty(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = _make_typer_context(_make_cli_ctx(password=None))

    def _explode_prompt(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("typer.prompt must not be called in non-TTY mode")

    monkeypatch.setattr(typer, "prompt", _explode_prompt)
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)

    @cli_error_handler
    def command(_ctx: typer.Context) -> None:
        raise RefreshTokenExpiredError("refresh rejected")

    with pytest.raises(click.exceptions.Exit):
        command(ctx)

    captured = capsys.readouterr()
    assert "Re-login required" in captured.out


def test_refresh_token_expired_reraises_when_explicit_password(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = _make_typer_context(_make_cli_ctx(password="explicit"))

    def _explode_prompt(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("typer.prompt must not be called with --password set")

    monkeypatch.setattr(typer, "prompt", _explode_prompt)
    monkeypatch.setattr("sys.stdin.isatty", _isatty_true)

    @cli_error_handler
    def command(_ctx: typer.Context) -> None:
        raise RefreshTokenExpiredError("refresh rejected")

    with pytest.raises(click.exceptions.Exit):
        command(ctx)

    captured = capsys.readouterr()
    assert "Re-login required" in captured.out


def test_refresh_token_expired_only_retries_once(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    ctx = _make_typer_context(_make_cli_ctx(password=None))

    calls: list[str | None] = []

    def _fake_prompt(*_args: object, **_kwargs: object) -> str:
        return "still-wrong"

    monkeypatch.setattr(typer, "prompt", _fake_prompt)
    monkeypatch.setattr("sys.stdin.isatty", _isatty_true)

    @cli_error_handler
    def command(_ctx: typer.Context) -> None:
        calls.append(_ctx.obj.password)
        raise AuthenticationError("invalid credentials")

    with pytest.raises(click.exceptions.Exit):
        command(ctx)

    captured = capsys.readouterr()
    assert "Authentication failed" in captured.out
    # Retry is not attempted unless the FIRST error is RefreshTokenExpiredError.
    assert calls == [None]
