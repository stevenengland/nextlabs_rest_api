from __future__ import annotations

import functools
from collections.abc import Callable
from typing import ParamSpec, TypeVar

import typer

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
            raise typer.Exit(code=1) from exc

    return wrapper
