from __future__ import annotations

import click
import pytest
import typer

from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk.exceptions import ApiError, AuthenticationError


def _ctx(verbose: int) -> typer.Context:
    cli_ctx = CliContext(
        base_url=None,
        username=None,
        password=None,
        client_id="cid",
        client_secret=None,
        pdp_url=None,
        json_output=False,
        verify=None,
        timeout=30.0,
        verbose=verbose,
    )
    ctx = typer.Context(click.Command("x"))
    ctx.obj = cli_ctx
    return ctx


def _full_auth_error() -> AuthenticationError:
    return AuthenticationError(
        message="Token acquisition failed: HTTP 500",
        status_code=500,
        response_body="server went boom",
        request_method="POST",
        request_url="https://srv/cas/oidc/accessToken",
    )


def _run_failing(exc: Exception, verbose: int):
    @cli_error_handler
    def failing(ctx: typer.Context):
        raise exc

    with pytest.raises(click.exceptions.Exit):
        failing(_ctx(verbose=verbose))


def test_verbose_zero_prints_only_base_message(capsys: pytest.CaptureFixture[str]):
    _run_failing(_full_auth_error(), verbose=0)

    captured = capsys.readouterr()
    assert "Authentication failed" in captured.out
    assert "srv/cas/oidc/accessToken" not in (captured.out + captured.err)


def test_verbose_one_prints_request_context_on_stderr(
    capsys: pytest.CaptureFixture[str],
):
    _run_failing(_full_auth_error(), verbose=1)

    captured = capsys.readouterr()
    assert "Authentication failed" in captured.out
    assert "POST" in captured.err
    assert "https://srv/cas/oidc/accessToken" in captured.err
    assert "500" in captured.err
    assert "server went boom" in captured.err


def test_verbose_one_non_nextlabs_error_unchanged(capsys: pytest.CaptureFixture[str]):
    _run_failing(typer.BadParameter("missing X"), verbose=1)

    captured = capsys.readouterr()
    assert "missing X" in captured.out
    assert "request:" not in captured.err


def test_verbose_one_with_partial_exception_fields(
    capsys: pytest.CaptureFixture[str],
):
    _run_failing(AuthenticationError(message="no response yet"), verbose=1)

    captured = capsys.readouterr()
    assert "None" not in captured.err


def test_verbose_one_prints_envelope_status_code(
    capsys: pytest.CaptureFixture[str],
):
    _run_failing(
        ApiError(
            message="No data found",
            status_code=200,
            response_body='{"statusCode":"5000","message":"No data found"}',
            request_method="GET",
            request_url="https://srv/console/api/v1/policy/mgmt/100",
            envelope_status_code="5000",
            envelope_message="No data found",
        ),
        verbose=1,
    )

    captured = capsys.readouterr()
    assert "API error: No data found" in captured.out
    assert "envelope:" in captured.err
    assert "statusCode=5000" in captured.err


def test_verbose_zero_hides_envelope_status_code(
    capsys: pytest.CaptureFixture[str],
):
    _run_failing(
        ApiError(
            message="No data found",
            status_code=200,
            envelope_status_code="5000",
            envelope_message="No data found",
        ),
        verbose=0,
    )

    captured = capsys.readouterr()
    assert "envelope:" not in captured.err
