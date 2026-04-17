from __future__ import annotations

import click
import pytest
import typer

from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk.exceptions import AuthenticationError


def _ctx(verbose: int) -> typer.Context:
    cli_ctx = CliContext(
        base_url=None,
        username=None,
        password=None,
        client_id="cid",
        client_secret=None,
        pdp_url=None,
        json_output=False,
        no_verify=False,
        timeout=30.0,
        verbose=verbose,
    )
    command = click.Command("x")
    ctx = typer.Context(command)
    ctx.obj = cli_ctx
    return ctx


def test_verbose_zero_prints_only_base_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    @cli_error_handler
    def failing(ctx: typer.Context) -> None:
        raise AuthenticationError(
            message="Token acquisition failed: HTTP 500",
            status_code=500,
            response_body="boom",
            request_method="POST",
            request_url="https://srv/cas/oidc/accessToken",
        )

    with pytest.raises(click.exceptions.Exit):
        failing(_ctx(verbose=0))

    captured = capsys.readouterr()
    assert "Authentication failed" in captured.out
    assert "srv/cas/oidc/accessToken" not in (captured.out + captured.err)


def test_verbose_one_prints_request_context_on_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    @cli_error_handler
    def failing(ctx: typer.Context) -> None:
        raise AuthenticationError(
            message="Token acquisition failed: HTTP 500",
            status_code=500,
            response_body="server went boom",
            request_method="POST",
            request_url="https://srv/cas/oidc/accessToken",
        )

    with pytest.raises(click.exceptions.Exit):
        failing(_ctx(verbose=1))

    captured = capsys.readouterr()
    # Base message still on stdout
    assert "Authentication failed" in captured.out
    # Extra context on stderr
    assert "POST" in captured.err
    assert "https://srv/cas/oidc/accessToken" in captured.err
    assert "500" in captured.err
    assert "server went boom" in captured.err


def test_verbose_one_non_nextlabs_error_unchanged(
    capsys: pytest.CaptureFixture[str],
) -> None:
    @cli_error_handler
    def failing(ctx: typer.Context) -> None:
        raise typer.BadParameter("missing X")

    with pytest.raises(click.exceptions.Exit):
        failing(_ctx(verbose=1))

    captured = capsys.readouterr()
    assert "missing X" in captured.out
    # No context lines appended
    assert "request:" not in captured.err


def test_verbose_one_with_partial_exception_fields(
    capsys: pytest.CaptureFixture[str],
) -> None:
    @cli_error_handler
    def failing(ctx: typer.Context) -> None:
        raise AuthenticationError(message="no response yet")

    with pytest.raises(click.exceptions.Exit):
        failing(_ctx(verbose=1))

    captured = capsys.readouterr()
    # No placeholders like "None" in stderr
    assert "None" not in captured.err
