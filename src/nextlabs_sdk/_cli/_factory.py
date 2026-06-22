"""Factory for CLI sub-group Typer instances."""

from __future__ import annotations

import typer


def make_group(help_text: str) -> typer.Typer:
    """Construct a sub-group Typer that auto-shows help on bare invocation.

    Args:
        help_text: Help string shown in the group's usage screen.

    Returns:
        A Typer configured with ``no_args_is_help=True`` so invoking the
        group without a subcommand prints help instead of erroring.
    """
    return typer.Typer(help=help_text, no_args_is_help=True)
