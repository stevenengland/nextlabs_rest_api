"""Shared fixtures for the CLI test suite.

Centralizes stub/fixture wiring duplicated across the ``test_cli_*``
modules so a change to the mocked collaborator surface (client factory
stubbing, detail-renderer console capture, or the frozen-clock instant)
is made once.
"""

from __future__ import annotations

import io
import time
from typing import Any

import pytest
from mockito import mock, when
from rich.console import Console

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk.pdp import PdpClient

_FROZEN_NOW_MS = 1_800_000_000_000


@pytest.fixture
def stub_pdp_client() -> Any:
    """Stub ``make_pdp_client`` and return the mocked ``PdpClient``."""
    mock_client = mock(PdpClient)
    when(_client_factory).make_pdp_client(...).thenReturn(mock_client)
    return mock_client


@pytest.fixture
def rich_console() -> tuple[Console, io.StringIO]:
    """Build an in-memory ``Console`` for capturing detail-renderer output."""
    buf = io.StringIO()
    return Console(file=buf, force_terminal=False, width=120, color_system=None), buf


@pytest.fixture
def frozen_clock() -> int:
    """Freeze ``time.time`` and return the frozen instant in milliseconds."""
    when(time).time().thenReturn(_FROZEN_NOW_MS / 1000)
    return _FROZEN_NOW_MS
