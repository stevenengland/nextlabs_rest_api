from __future__ import annotations

import logging
from typing import Iterator

import pytest

from nextlabs_sdk._cli._logging_setup import configure_cli_logging


@pytest.fixture(autouse=True)
def _clear_handlers() -> Iterator[None]:  # pyright: ignore[reportUnusedFunction]
    logger = logging.getLogger("nextlabs_sdk")
    original = list(logger.handlers)
    yield
    logger.handlers = original


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
