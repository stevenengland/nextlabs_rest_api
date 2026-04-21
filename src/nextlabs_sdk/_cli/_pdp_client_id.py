"""Resolver for the PDP-specific OAuth client ID used by the CLI."""

from __future__ import annotations

import sys

import typer

from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._pdp_auth_source import PdpAuthSource

_CLOUDAZ_DEFAULT_CLIENT_ID = "ControlCenterOIDCClient"


def resolve_pdp_client_id(ctx: CliContext, flavor: PdpAuthSource) -> str:
    """Return the client ID to use for PDP token minting.

    Precedence:
      1. ``ctx.pdp_client_id`` (``--pdp-client-id`` / env var) always wins.
      2. For ``CLOUDAZ`` flavor, fall back to ``ctx.client_id`` unconditionally
         (never prompt — preserves current ``--pdp-auth=cloudaz`` UX).
      3. For ``PDP`` flavor, fall back to ``ctx.client_id`` only when it
         differs from the CloudAz default sentinel; otherwise prompt on TTY
         or raise ``typer.BadParameter``.
    """
    if ctx.pdp_client_id:
        return ctx.pdp_client_id
    if flavor is PdpAuthSource.CLOUDAZ:
        return ctx.client_id
    if ctx.client_id and ctx.client_id != _CLOUDAZ_DEFAULT_CLIENT_ID:
        return ctx.client_id
    if sys.stdin.isatty():
        return typer.prompt("PDP client ID")
    raise typer.BadParameter(
        "--pdp-client-id or NEXTLABS_PDP_CLIENT_ID is required for --pdp-auth=pdp",
    )
