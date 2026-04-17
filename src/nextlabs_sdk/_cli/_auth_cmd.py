from __future__ import annotations

from dataclasses import replace
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from nextlabs_sdk._auth._active_account._active_account import ActiveAccount
from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._account_menu import (
    AccountIdentifier,
    cache_key_for,
    known_accounts,
    select_account,
)
from nextlabs_sdk._cli._account_resolver import (
    build_active_store,
    build_file_cache,
)
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._expiry_format import format_expiry
from nextlabs_sdk._cli._output import print_success

auth_app = typer.Typer(help="Authentication commands")

_NO_ACCOUNTS_MESSAGE = "No cached accounts. Run `nextlabs auth login` to create one."
_NO_ACTIVE_MESSAGE = (
    "No active account. Run `nextlabs auth login` " "or `nextlabs auth use` to set one."
)
_EXIT_FAILURE = typer.Exit(code=1)
_ACCOUNTS_TITLE = "Cached accounts"

_STATUS_ALL_OPTION = typer.Option(
    "--all",
    help="List every cached account with its token validity.",
)
_USE_SELECTOR_ARGUMENT = typer.Argument(
    help="1-based index, or username@base_url. Omit for an interactive menu.",
)


def _apply_menu_defaults(
    base_url: str | None,
    username: str | None,
    cli_ctx: CliContext,
) -> tuple[str | None, str | None]:
    if base_url and username:
        return base_url, username
    accounts = known_accounts(build_file_cache(cli_ctx))
    if not accounts:
        return base_url, username
    selection = select_account(accounts)
    if selection is None:
        return base_url, username
    return (base_url or selection.base_url, username or selection.username)


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


def _set_active(cli_ctx: CliContext, account: AccountIdentifier) -> None:
    build_active_store(cli_ctx).save(
        ActiveAccount(
            base_url=account.base_url,
            username=account.username,
            client_id=account.client_id,
        ),
    )


def _resolve_active_target(cli_ctx: CliContext) -> AccountIdentifier:
    if cli_ctx.base_url and cli_ctx.username:
        return AccountIdentifier(
            base_url=cli_ctx.base_url,
            username=cli_ctx.username,
            client_id=cli_ctx.client_id,
        )
    pointer = build_active_store(cli_ctx).load()
    if pointer is None:
        typer.echo(_NO_ACTIVE_MESSAGE)
        raise _EXIT_FAILURE
    return AccountIdentifier(
        base_url=pointer.base_url,
        username=pointer.username,
        client_id=pointer.client_id,
    )


def _is_active(cli_ctx: CliContext, account: AccountIdentifier) -> bool:
    pointer = build_active_store(cli_ctx).load()
    if pointer is None:
        return False
    return (
        pointer.base_url == account.base_url
        and pointer.username == account.username
        and pointer.client_id == account.client_id
    )


def _account_validity(cli_ctx: CliContext, account: AccountIdentifier) -> str:
    cache = build_file_cache(cli_ctx)
    entry = cache.load(cache_key_for(account))
    if entry is None:
        return "no cached token"
    qualifier = "expired" if entry.is_expired() else "valid"
    parts = [f"{qualifier} (expires {format_expiry(entry.expires_at)}"]
    if entry.refresh_expires_at is not None:
        parts.append(f"; refresh expires {format_expiry(entry.refresh_expires_at)}")
    parts.append(")")
    return "".join(parts)


def _render_accounts_table(
    cli_ctx: CliContext,
    entries: list[AccountIdentifier],
    *,
    include_status: bool,
) -> None:
    headers = ["#", "Active", "Username", "Base URL", "Client ID"]
    if include_status:
        headers.append("Status")
    table = Table(title=_ACCOUNTS_TITLE)
    for header in headers:
        table.add_column(header)
    for idx, account in enumerate(entries, start=1):
        marker = "*" if _is_active(cli_ctx, account) else ""
        row = [
            str(idx),
            marker,
            account.username,
            account.base_url,
            account.client_id,
        ]
        if include_status:
            row.append(_account_validity(cli_ctx, account))
        table.add_row(*row)
    Console().print(table)


def _select_by_index(
    entries: list[AccountIdentifier],
    selector: str,
) -> AccountIdentifier:
    idx = int(selector)
    if 1 <= idx <= len(entries):
        return entries[idx - 1]
    typer.echo(f"No cached account at index {idx}.")
    raise _EXIT_FAILURE


def _select_by_user_at_url(
    entries: list[AccountIdentifier],
    selector: str,
) -> AccountIdentifier:
    username, _, base_url = selector.partition("@")
    for entry in entries:
        if entry.username == username and entry.base_url == base_url:
            return entry
    typer.echo(f"No cached account matches `{selector}`.")
    raise _EXIT_FAILURE


def _pick_account(
    entries: list[AccountIdentifier],
    selector: str | None,
) -> AccountIdentifier:
    if selector is None:
        chosen = select_account(entries, add_new_label=None)
        if chosen is None:  # pragma: no cover - never returned without label
            raise _EXIT_FAILURE
        return chosen
    if selector.isdigit():
        return _select_by_index(entries, selector)
    if "@" in selector:
        return _select_by_user_at_url(entries, selector)
    typer.echo("Selector must be a 1-based index or `username@base_url`.")
    raise _EXIT_FAILURE


# ─────────────────────────── commands ─────────────────────────────────────


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
    """Acquire a token, persist it, and mark this account as active."""
    cli_ctx: CliContext = ctx.obj
    resolved = _resolve_login_context(cli_ctx)
    client = _client_factory.make_cloudaz_client(resolved)
    client.authenticate()
    _set_active(
        resolved,
        AccountIdentifier(
            base_url=resolved.base_url or "",
            username=resolved.username or "",
            client_id=resolved.client_id,
        ),
    )
    print_success("Login successful; token cached")


@auth_app.command(name="logout")
@cli_error_handler
def logout(ctx: typer.Context) -> None:
    """Remove the cached token; defaults to the active account."""
    cli_ctx: CliContext = ctx.obj
    target = _resolve_active_target(cli_ctx)
    cache = build_file_cache(cli_ctx)
    cache.delete(cache_key_for(target))
    if _is_active(cli_ctx, target):
        build_active_store(cli_ctx).clear()
    print_success("Logged out; cache entry removed")


_STATUS_TITLE = "Auth status"
_STATUS_NONE = "—"


def _render_status_detail(
    target: AccountIdentifier,
    entry: CachedToken,
) -> None:
    status_text = "expired" if entry.is_expired() else "valid"
    refresh_text = (
        _STATUS_NONE
        if entry.refresh_expires_at is None
        else format_expiry(entry.refresh_expires_at)
    )
    table = Table(title=_STATUS_TITLE, show_header=False)
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Username", target.username)
    table.add_row("Base URL", target.base_url)
    table.add_row("Client ID", target.client_id)
    table.add_row("Status", status_text)
    table.add_row("Expires", format_expiry(entry.expires_at))
    table.add_row("Refresh expires", refresh_text)
    Console().print(table)


@auth_app.command(name="status")
@cli_error_handler
def status(
    ctx: typer.Context,
    show_all: Annotated[bool, _STATUS_ALL_OPTION] = False,
) -> None:
    """Show whether a valid cached token exists."""
    cli_ctx: CliContext = ctx.obj
    if show_all:
        _status_all(cli_ctx)
        return
    target = _resolve_active_target(cli_ctx)
    cache = build_file_cache(cli_ctx)
    entry = cache.load(cache_key_for(target))
    if entry is None:
        typer.echo("No cached token.")
        raise _EXIT_FAILURE
    _render_status_detail(target, entry)
    if entry.is_expired():
        raise _EXIT_FAILURE


def _status_all(cli_ctx: CliContext) -> None:
    accounts = known_accounts(build_file_cache(cli_ctx))
    if not accounts:
        typer.echo(_NO_ACCOUNTS_MESSAGE)
        raise _EXIT_FAILURE
    _render_accounts_table(cli_ctx, accounts, include_status=True)


@auth_app.command(name="accounts")
@cli_error_handler
def accounts(ctx: typer.Context) -> None:
    """List every cached account, marking the active one."""
    cli_ctx: CliContext = ctx.obj
    entries = known_accounts(build_file_cache(cli_ctx))
    if not entries:
        typer.echo(_NO_ACCOUNTS_MESSAGE)
        raise _EXIT_FAILURE
    _render_accounts_table(cli_ctx, entries, include_status=False)


@auth_app.command(name="use")
@cli_error_handler
def use(
    ctx: typer.Context,
    selector: Annotated[str | None, _USE_SELECTOR_ARGUMENT] = None,
) -> None:
    """Switch the active cached account."""
    cli_ctx: CliContext = ctx.obj
    entries = known_accounts(build_file_cache(cli_ctx))
    if not entries:
        typer.echo(_NO_ACCOUNTS_MESSAGE)
        raise _EXIT_FAILURE
    target = _pick_account(entries, selector)
    _set_active(cli_ctx, target)
    print_success(f"Active account: {target.username} @ {target.base_url}")
