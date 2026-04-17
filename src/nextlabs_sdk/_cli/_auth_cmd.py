from __future__ import annotations

import typer

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import print_success

auth_app = typer.Typer(help="Authentication commands")


@auth_app.command(name="test")
@cli_error_handler
def test_auth(ctx: typer.Context) -> None:
    """Test CloudAz authentication credentials."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.operators.list_types()
    print_success("Authentication successful")


@auth_app.command(name="login")
@cli_error_handler
def login(ctx: typer.Context) -> None:
    """Acquire a token and persist it to the file token cache."""
    cli_ctx: CliContext = ctx.obj
    if not cli_ctx.password:
        raise typer.BadParameter("--password or NEXTLABS_PASSWORD is required")
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.operators.list_types()
    print_success("Login successful; token cached")


@auth_app.command(name="logout")
@cli_error_handler
def logout(ctx: typer.Context) -> None:
    """Remove the cached token for this base URL/username/client."""
    cli_ctx: CliContext = ctx.obj
    if not (cli_ctx.base_url and cli_ctx.username):
        raise typer.BadParameter(
            "--base-url and --username are required to identify the cache entry",
        )
    cache = _client_factory._build_file_cache(cli_ctx)
    cache.delete(_client_factory._cache_key(cli_ctx))
    print_success("Logged out; cache entry removed")


@auth_app.command(name="status")
@cli_error_handler
def status(ctx: typer.Context) -> None:
    """Show whether a valid cached token exists."""
    cli_ctx: CliContext = ctx.obj
    if not (cli_ctx.base_url and cli_ctx.username):
        typer.echo("No cache entry: --base-url and --username are required.")
        raise typer.Exit(code=1)
    cache = _client_factory._build_file_cache(cli_ctx)
    entry = cache.load(_client_factory._cache_key(cli_ctx))
    if entry is None:
        typer.echo("No cached token.")
        raise typer.Exit(code=1)
    if entry.is_expired():
        typer.echo("Cached token is expired.")
        raise typer.Exit(code=1)
    typer.echo(f"Cached token is valid (expires_at={entry.expires_at}).")
