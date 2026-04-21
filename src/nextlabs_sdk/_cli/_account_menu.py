from __future__ import annotations

from dataclasses import dataclass

import click
import typer

from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache
from nextlabs_sdk._cli._cache_key import cache_key_for as cache_key_for
from nextlabs_sdk._cli._cache_key import parse_cache_key as _parse_cache_key


@dataclass(frozen=True)
class AccountIdentifier:
    """Identifying tuple of a cached account."""

    base_url: str
    username: str
    client_id: str
    kind: str = "cloudaz"


def parse_cache_key(key: str) -> AccountIdentifier | None:
    """Parse a token-cache key into account identifiers, or ``None`` if malformed."""
    parsed = _parse_cache_key(key)
    if parsed is None:
        return None
    base_url, username, client_id, kind = parsed
    return AccountIdentifier(
        base_url=base_url,
        username=username,
        client_id=client_id,
        kind=kind,
    )


def known_accounts(cache: FileTokenCache) -> list[AccountIdentifier]:
    """Return all parseable accounts from the token cache, in insertion order."""
    parsed: list[AccountIdentifier] = []
    for key in cache.keys():
        entry = parse_cache_key(key)
        if entry is not None:
            parsed.append(entry)
    return parsed


def select_account(
    accounts: list[AccountIdentifier],
    *,
    add_new_label: str | None = "Add new",
) -> AccountIdentifier | None:
    """Prompt the user to pick a cached account.

    Returns the chosen account, or ``None`` if the user picked ``Add new``
    (only offered when ``add_new_label`` is non-empty).
    """
    typer.echo("Cached accounts:")
    for idx, account in enumerate(accounts, start=1):
        label = _account_label(account)
        typer.echo(f"  {idx}) {label}")
    if add_new_label:
        add_new_idx = len(accounts) + 1
        typer.echo(f"  {add_new_idx}) {add_new_label}")
        upper = add_new_idx
    else:
        upper = len(accounts)
    choice = typer.prompt(
        "Select an account",
        type=click.IntRange(1, upper),
        default=1,
    )
    if add_new_label and choice == len(accounts) + 1:
        return None
    return accounts[choice - 1]


def _account_label(account: AccountIdentifier) -> str:
    if account.kind == "pdp":
        return f"[pdp] @ {account.base_url}"
    return f"{account.username} @ {account.base_url}"
