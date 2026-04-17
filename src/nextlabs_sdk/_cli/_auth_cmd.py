from __future__ import annotations

from dataclasses import replace

import click
import typer

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import print_success

auth_app = typer.Typer(help="Authentication commands")

_TOKEN_PATH_SUFFIX = "/cas/oidc/accessToken"


def _parse_cache_key(key: str) -> tuple[str, str, str] | None:
    parts = key.split("|")
    if len(parts) != 3:
        return None
    base_part, username, client_id = parts
    if not base_part.endswith(_TOKEN_PATH_SUFFIX):
        return None
    base_url = base_part[: -len(_TOKEN_PATH_SUFFIX)]
    if not (base_url and username and client_id):
        return None
    return base_url, username, client_id


def _known_accounts(cli_ctx: CliContext) -> list[tuple[str, str, str]]:
    cache = _client_factory._build_file_cache(cli_ctx)
    parsed: list[tuple[str, str, str]] = []
    for key in cache.keys():
        entry = _parse_cache_key(key)
        if entry is not None:
            parsed.append(entry)
    return parsed


def _select_account(
    accounts: list[tuple[str, str, str]],
) -> tuple[str, str, str] | None:
    typer.echo("Cached accounts:")
    for idx, (base_url, username, _client_id) in enumerate(accounts, start=1):
        typer.echo(f"  {idx}) {username} @ {base_url}")
    add_new_idx = len(accounts) + 1
    typer.echo(f"  {add_new_idx}) Add new")
    choice = typer.prompt(
        "Select an account",
        type=click.IntRange(1, add_new_idx),
        default=1,
    )
    if choice == add_new_idx:
        return None
    return accounts[choice - 1]


def _apply_menu_defaults(
    base_url: str | None,
    username: str | None,
    cli_ctx: CliContext,
) -> tuple[str | None, str | None]:
    if base_url and username:
        return base_url, username
    accounts = _known_accounts(cli_ctx)
    if not accounts:
        return base_url, username
    selection = _select_account(accounts)
    if selection is None:
        return base_url, username
    picked_base, picked_user, _picked_client = selection
    return (base_url or picked_base, username or picked_user)


def _resolve_login_context(cli_ctx: CliContext) -> CliContext:
    base_url, username = _apply_menu_defaults(
        cli_ctx.base_url,
        cli_ctx.username,
        cli_ctx,
    )
    if not base_url:
        base_url = typer.prompt("Base URL")
    if not username:
        username = typer.prompt("Username")
    password = cli_ctx.password or typer.prompt("Password", hide_input=True)
    return replace(
        cli_ctx,
        base_url=base_url,
        username=username,
        password=password,
    )


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
    resolved = _resolve_login_context(cli_ctx)
    client = _client_factory.make_cloudaz_client(resolved)
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
