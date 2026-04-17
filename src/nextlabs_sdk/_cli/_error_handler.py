from __future__ import annotations

import functools
from collections.abc import Callable
from typing import ParamSpec, TypeVar

import typer
from rich.console import Console

from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._output import print_error
from nextlabs_sdk.exceptions import (
    AuthenticationError,
    NextLabsError,
    NotFoundError,
    RequestTimeoutError,
    TransportError,
)

ParamSpec_T = ParamSpec("ParamSpec_T")
ReturnType_T = TypeVar("ReturnType_T")

_BODY_PREVIEW_LIMIT = 2000


def _error_prefix(exc: NextLabsError) -> str:
    if isinstance(exc, AuthenticationError):
        return "Authentication failed"
    if isinstance(exc, NotFoundError):
        return "Not found"
    if isinstance(exc, RequestTimeoutError):
        return "Request timed out"
    if isinstance(exc, TransportError):
        return "Connection error"
    return "API error"


def _format_error_message(exc: BaseException) -> str:
    if isinstance(exc, typer.BadParameter):
        return str(exc)
    if isinstance(exc, NextLabsError):
        return f"{_error_prefix(exc)}: {exc.message}"
    return f"Unexpected error: {exc}"


def _extract_cli_context(args: tuple[object, ...]) -> CliContext | None:
    for arg in args:
        if isinstance(arg, typer.Context) and isinstance(arg.obj, CliContext):
            return arg.obj
    return None


def _format_body_preview(body: str, total_length: int) -> str:
    if body == "":
        return "<empty>"
    if total_length > _BODY_PREVIEW_LIMIT:
        return (
            f"{body[:_BODY_PREVIEW_LIMIT]}" f"… (truncated, {total_length} bytes total)"
        )
    return body


def _print_verbose_context(exc: NextLabsError) -> None:
    stderr = Console(stderr=True)
    if exc.request_url:
        method = exc.request_method or ""
        stderr.print(f"  request: {method} {exc.request_url}".rstrip())
    if exc.status_code is not None:
        stderr.print(f"  status:  {exc.status_code}")
    if exc.envelope_status_code is not None:
        stderr.print(f"  envelope: statusCode={exc.envelope_status_code}")
    body = exc.response_body
    if body is not None:
        stderr.print(f"  body:    {_format_body_preview(body, len(body))}")


def _maybe_print_verbose(exc: BaseException, args: tuple[object, ...]) -> None:
    if not isinstance(exc, NextLabsError):
        return
    cli_ctx = _extract_cli_context(args)
    if cli_ctx is None or cli_ctx.verbose < 1:
        return
    _print_verbose_context(exc)


def cli_error_handler(
    func: Callable[ParamSpec_T, ReturnType_T],
) -> Callable[ParamSpec_T, ReturnType_T]:
    @functools.wraps(func)
    def wrapper(*args: ParamSpec_T.args, **kwargs: ParamSpec_T.kwargs) -> ReturnType_T:
        try:
            return func(*args, **kwargs)
        except typer.Exit:
            raise
        except Exception as exc:
            print_error(_format_error_message(exc))
            _maybe_print_verbose(exc, args)
            raise typer.Exit(code=1) from exc

    return wrapper
