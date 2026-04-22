from __future__ import annotations

import logging
from typing import Iterator

import pytest

from nextlabs_sdk._cli._logging_setup import configure_cli_logging


@pytest.fixture(autouse=True)
def _clear_handlers() -> Iterator[None]:  # pyright: ignore[reportUnusedFunction]
    logger = logging.getLogger("nextlabs_sdk")
    original_handlers = list(logger.handlers)
    original_level = logger.level
    yield
    logger.handlers = original_handlers
    logger.setLevel(original_level)


def _our_handlers() -> list[logging.Handler]:
    logger = logging.getLogger("nextlabs_sdk")
    return [
        h for h in logger.handlers if getattr(h, "name", None) == "nextlabs-cli-verbose"
    ]


def test_level_0_attaches_no_handler() -> None:
    configure_cli_logging(0)

    assert _our_handlers() == []


def test_level_1_attaches_no_handler() -> None:
    configure_cli_logging(1)

    assert _our_handlers() == []


def test_level_2_attaches_stderr_handler_at_debug() -> None:
    configure_cli_logging(2)

    handlers = _our_handlers()
    assert len(handlers) == 1
    assert handlers[0].level == logging.DEBUG


def test_idempotent_second_call_does_not_duplicate_handler() -> None:
    configure_cli_logging(2)
    configure_cli_logging(2)

    assert len(_our_handlers()) == 1


def test_level_2_sets_default_body_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    from nextlabs_sdk import _logging

    monkeypatch.delenv("NEXTLABS_LOG_BODY_LIMIT", raising=False)
    _logging.set_effective_body_limit(999)
    configure_cli_logging(2)

    assert _logging.get_effective_body_limit() == 2000


def test_level_3_sets_unlimited_body_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    from nextlabs_sdk import _logging

    monkeypatch.delenv("NEXTLABS_LOG_BODY_LIMIT", raising=False)
    _logging.set_effective_body_limit(2000)
    try:
        configure_cli_logging(3)
        assert _logging.get_effective_body_limit() is None
    finally:
        _logging.set_effective_body_limit(2000)


def test_env_overrides_verbose(monkeypatch: pytest.MonkeyPatch) -> None:
    from nextlabs_sdk import _logging

    monkeypatch.setenv("NEXTLABS_LOG_BODY_LIMIT", "123")
    _logging.set_effective_body_limit(2000)
    try:
        configure_cli_logging(3)
        assert _logging.get_effective_body_limit() == 123
    finally:
        _logging.set_effective_body_limit(2000)


def test_env_zero_means_unlimited_at_vv(monkeypatch: pytest.MonkeyPatch) -> None:
    from nextlabs_sdk import _logging

    monkeypatch.setenv("NEXTLABS_LOG_BODY_LIMIT", "0")
    _logging.set_effective_body_limit(2000)
    try:
        configure_cli_logging(2)
        assert _logging.get_effective_body_limit() is None
    finally:
        _logging.set_effective_body_limit(2000)


def test_level_below_2_leaves_limit_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nextlabs_sdk import _logging

    monkeypatch.setenv("NEXTLABS_LOG_BODY_LIMIT", "42")
    _logging.set_effective_body_limit(2000)
    try:
        configure_cli_logging(1)
        assert _logging.get_effective_body_limit() == 2000
    finally:
        _logging.set_effective_body_limit(2000)
