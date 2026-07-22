from __future__ import annotations

import ssl

import pytest

from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._output_format import OutputFormat
from nextlabs_sdk._cli._ssl_retry import (
    SslRetryPrompter,
    is_ssl_verify_error,
)
from nextlabs_sdk.exceptions import TransportError


def _wrap(outer: Exception, cause: BaseException) -> Exception:
    outer.__cause__ = cause
    return outer


def test_detects_direct_ssl_cert_verify_error() -> None:
    exc = ssl.SSLCertVerificationError("certificate verify failed")
    assert is_ssl_verify_error(exc) is True


def test_detects_ssl_error_with_verify_code() -> None:
    exc = ssl.SSLError("bad cert")
    setattr(exc, "verify_code", 18)
    setattr(exc, "verify_message", "self-signed certificate")
    assert is_ssl_verify_error(exc) is True


def test_detects_ssl_error_wrapped_in_transport_error_via_cause() -> None:
    cause = ssl.SSLCertVerificationError("certificate verify failed")
    wrapped = _wrap(TransportError("Connection error"), cause)
    assert is_ssl_verify_error(wrapped) is True


def test_returns_false_for_unrelated_oserror() -> None:
    assert is_ssl_verify_error(OSError("connection refused")) is False


def test_returns_false_for_ssl_error_without_verify_code() -> None:
    exc = ssl.SSLError("handshake failure")
    assert is_ssl_verify_error(exc) is False


# ─────────────────── SslRetryPrompter tests ────────────────────


def _ctx(verify: bool | None = None, verbose: int = 0) -> CliContext:
    return CliContext(
        base_url="https://example.com",
        username="u",
        password="p",
        client_id="cid",
        client_secret=None,
        pdp_url=None,
        output_format=OutputFormat.TABLE,
        verify=verify,
        timeout=30.0,
        verbose=verbose,
    )


def _make_prompter(
    *,
    isatty: bool = True,
    confirm_answer: bool = True,
    confirms: list[tuple[str, bool]] | None = None,
) -> SslRetryPrompter:
    def _isatty() -> bool:
        return isatty

    def _confirm(text: str, *, default: bool = False) -> bool:
        if confirms is not None:
            confirms.append((text, default))
        return confirm_answer

    return SslRetryPrompter(isatty=_isatty, confirm=_confirm)


def _wrap_ssl_error() -> TransportError:
    cause = ssl.SSLCertVerificationError("certificate verify failed")
    wrapped = TransportError("Connection error")
    wrapped.__cause__ = cause
    return wrapped


def test_attempt_succeeds_on_first_call_returns_original_ctx() -> None:
    calls: list[CliContext] = []

    def _attempt(ctx: CliContext) -> None:
        calls.append(ctx)

    prompter = _make_prompter()
    original = _ctx()

    used = prompter.run_with_ssl_retry(
        attempt=_attempt,
        cli_ctx=original,
        target_url="https://example.com",
    )

    assert used is original
    assert calls == [original]


def test_ssl_error_on_tty_with_yes_retries_with_verify_false() -> None:
    calls: list[CliContext] = []

    def _attempt(ctx: CliContext) -> None:
        calls.append(ctx)
        if len(calls) == 1:
            raise _wrap_ssl_error()

    confirms: list[tuple[str, bool]] = []
    prompter = _make_prompter(isatty=True, confirm_answer=True, confirms=confirms)
    original = _ctx()

    used = prompter.run_with_ssl_retry(
        attempt=_attempt,
        cli_ctx=original,
        target_url="https://example.com",
    )

    assert len(calls) == 2
    assert calls[0].verify is None
    assert calls[1].verify is False
    assert used.verify is False
    assert len(confirms) == 1
    assert "Retry with SSL verification disabled?" in confirms[0][0]
    assert confirms[0][1] is False


def test_ssl_error_on_tty_with_no_reraises_original() -> None:
    def _attempt(_ctx: CliContext) -> None:
        raise _wrap_ssl_error()

    prompter = _make_prompter(isatty=True, confirm_answer=False)

    with pytest.raises(TransportError):
        prompter.run_with_ssl_retry(
            attempt=_attempt,
            cli_ctx=_ctx(),
            target_url="https://example.com",
        )


def test_non_tty_reraises_without_confirm() -> None:
    confirms: list[tuple[str, bool]] = []

    def _attempt(_ctx: CliContext) -> None:
        raise _wrap_ssl_error()

    prompter = _make_prompter(isatty=False, confirms=confirms)

    with pytest.raises(TransportError):
        prompter.run_with_ssl_retry(
            attempt=_attempt,
            cli_ctx=_ctx(),
            target_url="https://example.com",
        )

    assert confirms == []


def test_explicit_verify_false_skips_prompt_and_reraises() -> None:
    confirms: list[tuple[str, bool]] = []

    def _attempt(_ctx: CliContext) -> None:
        raise _wrap_ssl_error()

    prompter = _make_prompter(isatty=True, confirms=confirms)

    with pytest.raises(TransportError):
        prompter.run_with_ssl_retry(
            attempt=_attempt,
            cli_ctx=_ctx(verify=False),
            target_url="https://example.com",
        )

    assert confirms == []


def test_non_ssl_transport_error_propagates_without_prompt() -> None:
    confirms: list[tuple[str, bool]] = []

    def _attempt(_ctx: CliContext) -> None:
        raise TransportError("Connection refused")

    prompter = _make_prompter(isatty=True, confirms=confirms)

    with pytest.raises(TransportError, match="Connection refused"):
        prompter.run_with_ssl_retry(
            attempt=_attempt,
            cli_ctx=_ctx(),
            target_url="https://example.com",
        )

    assert confirms == []


def test_retry_also_fails_propagates_retry_error() -> None:
    attempts: list[CliContext] = []

    def _attempt(ctx: CliContext) -> None:
        attempts.append(ctx)
        if len(attempts) == 1:
            raise _wrap_ssl_error()
        raise TransportError("second-failure")

    prompter = _make_prompter(isatty=True, confirm_answer=True)

    with pytest.raises(TransportError, match="second-failure"):
        prompter.run_with_ssl_retry(
            attempt=_attempt,
            cli_ctx=_ctx(),
            target_url="https://example.com",
        )

    assert len(attempts) == 2
    assert attempts[1].verify is False
