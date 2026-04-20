"""Inline interactive re-auth policy for CLI commands.

Encapsulates the behavior described in issue #42: when the SDK signals
that the cached refresh token is no longer usable, interactive callers
are given exactly one opportunity to re-enter their password so the
command can be transparently retried. Non-interactive callers see the
original :class:`RefreshTokenExpiredError` unchanged so scripts and
pipelines can handle it deterministically.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Protocol, TypeVar

import typer

from nextlabs_sdk.exceptions import RefreshTokenExpiredError

ClientT = TypeVar("ClientT")
ResultT = TypeVar("ResultT")

_DEFAULT_PROMPT_LABEL = "Password (re-auth required)"


class _PromptFn(Protocol):
    def __call__(self, text: str, *, hide_input: bool = ...) -> str: ...


class ReauthPrompter:
    """Drives the "try once, prompt, retry once" re-auth policy.

    Callers supply two closures:

    * ``build_client(password_override)`` — constructs the SDK client.
      ``password_override`` is ``None`` on the first call; on retry it
      carries the password the user just entered.
    * ``action(client)`` — executes the command's API call(s) against
      the client and returns the command's result.

    The prompter runs ``action(build_client(None))`` and returns its
    result. If the SDK raises :class:`RefreshTokenExpiredError` and the
    caller is at an interactive TTY with no explicit password already
    configured, the prompter asks for a password once, rebuilds the
    client via ``build_client(password)``, and retries the action
    exactly once. Any further error — including a second
    :class:`RefreshTokenExpiredError` or any other
    :class:`~nextlabs_sdk.exceptions.AuthenticationError` — propagates
    unchanged.
    """

    def __init__(
        self,
        *,
        isatty: Callable[[], bool] | None = None,
        prompt: _PromptFn | None = None,
    ) -> None:
        self._isatty = sys.stdin.isatty if isatty is None else isatty
        self._prompt = typer.prompt if prompt is None else prompt

    def run_with_reauth(
        self,
        *,
        build_client: Callable[[str | None], ClientT],
        action: Callable[[ClientT], ResultT],
        has_explicit_password: bool,
        prompt_label: str = _DEFAULT_PROMPT_LABEL,
    ) -> ResultT:
        client = build_client(None)
        try:
            return action(client)
        except RefreshTokenExpiredError:
            if has_explicit_password or not self._isatty():
                raise
            password = self._prompt(prompt_label, hide_input=True)
            return action(build_client(password))
