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
)

ParamSpec_T = ParamSpec("ParamSpec_T")
ReturnType_T = TypeVar("ReturnType_T")


def _error_prefix(exc: NextLabsError) -> str:
    if isinstance(exc, AuthenticationError):
        return "Authentication failed"
    if isinstance(exc, NotFoundError):
        return "Not found"
    return "API error"


def cli_error_handler(
    func: Callable[ParamSpec_T, ReturnType_T],
) -> Callable[ParamSpec_T, ReturnType_T]:
    @functools.wraps(func)
    def wrapper(*args: ParamSpec_T.args, **kwargs: ParamSpec_T.kwargs) -> ReturnType_T:
        try:
            return func(*args, **kwargs)
        except NextLabsError as exc:
            print_error(f"{_error_prefix(exc)}: {exc.message}")
            raise typer.Exit(code=1) from exc

    return wrapper
