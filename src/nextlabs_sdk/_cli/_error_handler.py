from __future__ import annotations

import functools
import inspect
import sys
from collections.abc import Callable
from dataclasses import replace
from typing import ParamSpec, TypeVar

import typer
from rich.console import Console

from nextlabs_sdk._cli._account_resolver import resolve_account
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._output import print_error
from nextlabs_sdk.exceptions import (
    AuthenticationError,
    NextLabsError,
    NotFoundError,
    PdpStatusError,
    RefreshTokenExpiredError,
    RequestTimeoutError,
    TokenCacheError,
    TransportError,
)

ParamSpec_T = ParamSpec("ParamSpec_T")
ReturnType_T = TypeVar("ReturnType_T")

_BODY_PREVIEW_LIMIT = 2000


_ErrorPrefixPair = tuple[type[NextLabsError], str]
_ERROR_PREFIXES: tuple[_ErrorPrefixPair, ...] = (
    (TokenCacheError, "Token cache error"),
    (RefreshTokenExpiredError, "Re-login required"),
    (AuthenticationError, "Authentication failed"),
    (NotFoundError, "Not found"),
    (RequestTimeoutError, "Request timed out"),
    (TransportError, "Connection error"),
    (PdpStatusError, "PDP rejected the request"),
)


def _error_prefix(exc: NextLabsError) -> str:
    for exc_type, prefix in _ERROR_PREFIXES:
        if isinstance(exc, exc_type):
            return prefix
    return "API error"


def _format_error_message(exc: BaseException) -> str:
    if isinstance(exc, typer.BadParameter):
        return str(exc)
    if isinstance(exc, NextLabsError):
        return f"{_error_prefix(exc)}: {exc.message}"
    return f"Unexpected error: {exc}"


def _extract_typer_context(
    func: Callable[ParamSpec_T, ReturnType_T],
    args: tuple[object, ...],
    kwargs: dict[str, object] | None = None,
) -> typer.Context | None:
    sig = inspect.signature(func)
    ctx_param = next(
        (
            name
            for name in sig.parameters
            if sig.parameters[name].annotation in (typer.Context, "typer.Context")
        ),
        None,
    )
    if ctx_param is None:
        return None
    try:
        bound = sig.bind_partial(*args, **(kwargs or {}))
    except TypeError:
        return None
    return bound.arguments.get(ctx_param)


def _extract_cli_context(
    func: Callable[ParamSpec_T, ReturnType_T],
    args: tuple[object, ...],
    kwargs: dict[str, object] | None = None,
) -> CliContext | None:
    ctx = _extract_typer_context(func, args, kwargs)
    if ctx is None or not isinstance(ctx.obj, CliContext):
        return None
    return ctx.obj


def _reauth_prompt_label(cli_ctx: CliContext) -> str:
    if cli_ctx.username:
        target = cli_ctx.username
        if cli_ctx.base_url:
            target = f"{target}@{cli_ctx.base_url}"
        return f"Password for {target} (re-auth required)"

    account = resolve_account(cli_ctx)
    if account is not None and account.username:
        return f"Password for {account.username}@{account.base_url} (re-auth required)"

    return "Password for <unknown user> (re-auth required)"


def _prepare_reauth(
    func: Callable[ParamSpec_T, ReturnType_T],
    args: tuple[object, ...],
    kwargs: dict[str, object] | None = None,
) -> bool:
    """Mutate the typer context with a freshly prompted password.

    Returns ``True`` if an inline re-auth retry should be attempted,
    ``False`` if the caller should let the original error propagate.
    """
    typer_ctx = _extract_typer_context(func, args, kwargs)
    if typer_ctx is None or not isinstance(typer_ctx.obj, CliContext):
        return False
    cli_ctx = typer_ctx.obj
    if cli_ctx.password:
        return False
    if not sys.stdin.isatty():
        return False
    password = typer.prompt(_reauth_prompt_label(cli_ctx), hide_input=True)
    typer_ctx.obj = replace(cli_ctx, password=password)
    return True


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


def _maybe_print_verbose(
    exc: BaseException,
    func: Callable[ParamSpec_T, ReturnType_T],
    args: tuple[object, ...],
    kwargs: dict[str, object] | None = None,
) -> None:
    if not isinstance(exc, NextLabsError):
        return
    cli_ctx = _extract_cli_context(func, args, kwargs)
    if cli_ctx is None or cli_ctx.verbose < 1:
        return
    _print_verbose_context(exc)


def _handle_exception(
    exc: BaseException,
    func: Callable[ParamSpec_T, ReturnType_T],
    args: tuple[object, ...],
    kwargs: dict[str, object] | None = None,
) -> None:
    print_error(_format_error_message(exc))
    _maybe_print_verbose(exc, func, args, kwargs)
    raise typer.Exit(code=1) from exc


def _run_with_reauth(
    func: Callable[ParamSpec_T, ReturnType_T],
    *args: ParamSpec_T.args,
    **kwargs: ParamSpec_T.kwargs,
) -> ReturnType_T:
    try:
        return func(*args, **kwargs)
    except RefreshTokenExpiredError:
        if not _prepare_reauth(func, args, kwargs):
            raise
        return func(*args, **kwargs)


def cli_error_handler(
    func: Callable[ParamSpec_T, ReturnType_T],
) -> Callable[ParamSpec_T, ReturnType_T]:
    @functools.wraps(func)
    def wrapper(*args: ParamSpec_T.args, **kwargs: ParamSpec_T.kwargs) -> ReturnType_T:
        try:
            return _run_with_reauth(func, *args, **kwargs)
        except typer.Exit:
            raise
        except Exception as exc:
            _handle_exception(exc, func, args, kwargs)
            raise  # unreachable; _handle_exception always raises

    return wrapper
