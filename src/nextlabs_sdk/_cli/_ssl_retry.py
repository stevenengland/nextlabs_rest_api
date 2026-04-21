"""Interactive SSL-retry policy for ``nextlabs auth login``.

When the server's TLS certificate cannot be verified, interactive
callers are offered exactly one opportunity to retry with verification
disabled. Non-interactive callers and callers who passed an explicit
``--verify`` / ``--no-verify`` see the original error unchanged.
"""

from __future__ import annotations

import ssl
import sys
from collections.abc import Callable
from dataclasses import replace
from typing import Protocol

import typer

from nextlabs_sdk._cli._context import CliContext

_MAX_CAUSE_DEPTH = 10


def is_ssl_verify_error(exc: BaseException) -> bool:
    """Return ``True`` iff ``exc`` is — or wraps — an SSL verify error.

    Walks ``__cause__`` and ``__context__`` up to a bounded depth so the
    helper works regardless of whether the caught exception is the raw
    :class:`ssl.SSLError` or a :class:`~nextlabs_sdk.exceptions.TransportError`
    that wrapped it.

    Args:
        exc: The exception to inspect.

    Returns:
        ``True`` when the chain contains an
        :class:`ssl.SSLCertVerificationError`, or an :class:`ssl.SSLError`
        whose ``verify_code`` attribute is truthy.
    """
    seen: set[int] = set()
    current: BaseException | None = exc
    depth = 0
    while current is not None and depth < _MAX_CAUSE_DEPTH:
        if id(current) in seen:
            return False
        seen.add(id(current))
        if _is_direct_ssl_verify_error(current):
            return True
        current = current.__cause__ or current.__context__
        depth += 1
    return False


def _is_direct_ssl_verify_error(exc: BaseException) -> bool:
    if isinstance(exc, ssl.SSLCertVerificationError):
        return True
    if isinstance(exc, ssl.SSLError):
        return bool(getattr(exc, "verify_code", None))
    return False


class _ConfirmFn(Protocol):
    def __call__(self, text: str, *, default: bool = ...) -> bool: ...


class SslRetryPrompter:
    """Runs a login ``attempt`` with a one-shot interactive SSL retry.

    Mirrors the DI shape of :class:`ReauthPrompter`. Callers supply an
    ``attempt(cli_ctx)`` callable; the prompter runs it, and if the call
    fails with an SSL verification error AND the caller is on a TTY AND
    ``cli_ctx.verify`` is ``None``, prompts once to retry with
    ``verify=False``. The returned :class:`CliContext` is the one that
    actually produced a successful call — callers should use it for any
    subsequent persistence so ``verify_ssl=False`` is recorded when
    retry succeeded.
    """

    def __init__(
        self,
        *,
        isatty: Callable[[], bool] | None = None,
        confirm: _ConfirmFn | None = None,
    ) -> None:
        self._isatty = sys.stdin.isatty if isatty is None else isatty
        self._confirm = typer.confirm if confirm is None else confirm

    def run_with_ssl_retry(
        self,
        *,
        attempt: Callable[[CliContext], None],
        cli_ctx: CliContext,
        target_url: str,
    ) -> CliContext:
        try:
            attempt(cli_ctx)
        except Exception as exc:
            if not self._should_offer_retry(exc, cli_ctx):
                raise
            typer.echo(f"SSL verification failed for {target_url}.")
            if not self._confirm(
                "Retry with SSL verification disabled?",
                default=False,
            ):
                raise
            retry_ctx = replace(cli_ctx, verify=False)
            attempt(retry_ctx)
            return retry_ctx
        return cli_ctx

    def _should_offer_retry(
        self,
        exc: BaseException,
        cli_ctx: CliContext,
    ) -> bool:
        if cli_ctx.verify is not None:
            return False
        if not self._isatty():
            return False
        return is_ssl_verify_error(exc)
