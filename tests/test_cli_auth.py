from __future__ import annotations

from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._operators import OperatorService
from nextlabs_sdk.exceptions import AuthenticationError

runner = CliRunner()

_GLOBAL_OPTS = (
    "--base-url",
    "https://example.com",
    "--username",
    "admin",
    "--password",
    "secret",
)


def test_auth_test_success() -> None:
    mock_client = mock(CloudAzClient)
    mock_ops = mock(OperatorService)
    mock_client.operators = mock_ops
    when(mock_ops).list_types().thenReturn(["STRING", "NUMBER"])
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "auth", "test"])

    assert result.exit_code == 0
    assert "successful" in result.output.lower()


def test_auth_test_failure() -> None:
    when(_client_factory).make_cloudaz_client(...).thenRaise(
        AuthenticationError(message="bad creds"),
    )

    result = runner.invoke(app, [*_GLOBAL_OPTS, "auth", "test"])

    assert result.exit_code == 1
    assert "Authentication failed" in result.output


def test_auth_test_missing_credentials() -> None:
    result = runner.invoke(app, ["--base-url", "https://x.com", "auth", "test"])

    assert result.exit_code == 1
    assert "username" in result.output.lower()
