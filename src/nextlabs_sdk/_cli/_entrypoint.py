"""Console-script entry point for the ``nextlabs`` CLI.

This shim exists so ``pip install nextlabs-sdk`` (without the ``[cli]``
extra) still gives a helpful error instead of a raw
``ModuleNotFoundError`` when the user runs ``nextlabs``. It imports
nothing from Typer/Rich at module load time and only delegates to the
real Typer app once we know the optional dependencies are installed.
"""

from __future__ import annotations

import importlib
import sys
from importlib import util as importlib_util

_CLI_EXTRA_MODULES: tuple[str, ...] = ("typer", "rich")
_INSTALL_HINT = "pip install 'nextlabs-sdk[cli]'"


def _missing_cli_modules() -> list[str]:
    return [
        name for name in _CLI_EXTRA_MODULES if importlib_util.find_spec(name) is None
    ]


def _print_missing_deps_message(missing: list[str]) -> None:
    joined = ", ".join(missing)
    sys.stderr.write(
        f"nextlabs CLI dependencies are not installed (missing: {joined}).\n"
        f"Install them with:\n\n    {_INSTALL_HINT}\n",
    )


def main() -> None:
    """Entry point registered as the ``nextlabs`` console script."""
    missing = _missing_cli_modules()
    if missing:
        _print_missing_deps_message(missing)
        sys.exit(1)

    app_module = importlib.import_module("nextlabs_sdk._cli._app")
    app_module.app()
