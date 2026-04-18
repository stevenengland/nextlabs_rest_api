from __future__ import annotations

import json
from typing import Any

import pytest
from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._system_config import SystemConfigService
from nextlabs_sdk._cloudaz._system_config_models import SystemConfig

runner = CliRunner()

_GLOBAL_OPTS = (
    "--base-url",
    "https://example.com",
    "--username",
    "admin",
    "--password",
    "secret",
)


@pytest.fixture
def stub() -> tuple[Any, Any]:
    mock_client = mock(CloudAzClient)
    mock_service = mock(SystemConfigService)
    mock_client.system_config = mock_service
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)
    return mock_client, mock_service


def _make_config() -> SystemConfig:
    return SystemConfig(settings={"theme": "dark", "locale": "en_US"})


def test_system_config_get_table(stub: tuple[Any, Any]) -> None:
    _, service = stub
    when(service).get().thenReturn(_make_config())

    result = runner.invoke(app, [*_GLOBAL_OPTS, "system-config", "get"])

    assert result.exit_code == 0
    assert "theme" in result.output
    assert "dark" in result.output
    assert "locale" in result.output


def test_system_config_get_json(stub: tuple[Any, Any]) -> None:
    _, service = stub
    when(service).get().thenReturn(_make_config())

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "-o", "json", "system-config", "get"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == {"theme": "dark", "locale": "en_US"}


def test_system_config_get_empty(stub: tuple[Any, Any]) -> None:
    _, service = stub
    when(service).get().thenReturn(SystemConfig(settings={}))

    result = runner.invoke(app, [*_GLOBAL_OPTS, "system-config", "get"])

    assert result.exit_code == 0
