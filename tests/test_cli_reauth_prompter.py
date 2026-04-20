from __future__ import annotations

from collections.abc import Callable
import pytest

from nextlabs_sdk._cli._reauth_prompter import ReauthPrompter
from nextlabs_sdk.exceptions import (
    AuthenticationError,
    NotFoundError,
    RefreshTokenExpiredError,
)


class _FakeClient:
    def __init__(self, password: str | None) -> None:
        self.password = password


def _make_build_client(log: list[str | None]) -> Callable[[str | None], _FakeClient]:
    def _build(password: str | None) -> _FakeClient:
        log.append(password)
        return _FakeClient(password)

    return _build


def _make_prompter(
    *,
    isatty: bool,
    password: str = "typed-pw",
    prompts: list[tuple[str, bool]] | None = None,
) -> ReauthPrompter:
    def _isatty() -> bool:
        return isatty

    def _prompt(text: str, *, hide_input: bool = False) -> str:
        if prompts is not None:
            prompts.append((text, hide_input))
        return password

    return ReauthPrompter(isatty=_isatty, prompt=_prompt)


def test_action_returns_directly_when_no_refresh_error():
    build_log: list[str | None] = []
    prompter = _make_prompter(isatty=True)

    result = prompter.run_with_reauth(
        build_client=_make_build_client(build_log),
        action=lambda client: f"ok-{client.password}",
        has_explicit_password=False,
    )

    assert result == "ok-None"
    assert build_log == [None]


def test_tty_reprompts_once_and_retries_with_new_password():
    build_log: list[str | None] = []
    prompts: list[tuple[str, bool]] = []
    prompter = _make_prompter(isatty=True, password="fresh-pw", prompts=prompts)

    calls: list[str | None] = []

    def _action(client: _FakeClient) -> str:
        calls.append(client.password)
        if len(calls) == 1:
            raise RefreshTokenExpiredError("expired")
        return f"retried-{client.password}"

    result = prompter.run_with_reauth(
        build_client=_make_build_client(build_log),
        action=_action,
        has_explicit_password=False,
        prompt_label="Password for user@host",
    )

    assert result == "retried-fresh-pw"
    assert build_log == [None, "fresh-pw"]
    assert prompts == [("Password for user@host", True)]


def test_non_tty_reraises_without_prompting():
    build_log: list[str | None] = []
    prompts: list[tuple[str, bool]] = []
    prompter = _make_prompter(isatty=False, prompts=prompts)

    def _action(_client: _FakeClient) -> None:
        raise RefreshTokenExpiredError("expired")

    with pytest.raises(RefreshTokenExpiredError):
        prompter.run_with_reauth(
            build_client=_make_build_client(build_log),
            action=_action,
            has_explicit_password=False,
        )

    assert prompts == []
    assert build_log == [None]


def test_explicit_password_skips_prompt_and_reraises():
    build_log: list[str | None] = []
    prompts: list[tuple[str, bool]] = []
    prompter = _make_prompter(isatty=True, prompts=prompts)

    def _action(_client: _FakeClient) -> None:
        raise RefreshTokenExpiredError("expired")

    with pytest.raises(RefreshTokenExpiredError):
        prompter.run_with_reauth(
            build_client=_make_build_client(build_log),
            action=_action,
            has_explicit_password=True,
        )

    assert prompts == []
    assert build_log == [None]


def test_retry_auth_failure_propagates_without_second_prompt():
    build_log: list[str | None] = []
    prompts: list[tuple[str, bool]] = []
    prompter = _make_prompter(isatty=True, prompts=prompts)

    def _action(_client: _FakeClient) -> None:
        if len(build_log) == 1:
            raise RefreshTokenExpiredError("expired")
        raise AuthenticationError("bad creds")

    with pytest.raises(AuthenticationError, match="bad creds"):
        prompter.run_with_reauth(
            build_client=_make_build_client(build_log),
            action=_action,
            has_explicit_password=False,
        )

    assert len(prompts) == 1
    assert build_log == [None, "typed-pw"]


def test_non_auth_errors_propagate_without_prompting():
    build_log: list[str | None] = []
    prompts: list[tuple[str, bool]] = []
    prompter = _make_prompter(isatty=True, prompts=prompts)

    def _action(_client: _FakeClient) -> None:
        raise NotFoundError("HTTP 404")

    with pytest.raises(NotFoundError):
        prompter.run_with_reauth(
            build_client=_make_build_client(build_log),
            action=_action,
            has_explicit_password=False,
        )

    assert prompts == []
    assert build_log == [None]
