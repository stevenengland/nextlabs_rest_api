from __future__ import annotations

from dataclasses import dataclass

from nextlabs_sdk._cli._output_format import OutputFormat


@dataclass(frozen=True)
class CliContext:
    """Global CLI options passed via typer.Context.obj."""

    base_url: str | None
    username: str | None
    password: str | None
    client_id: str
    client_secret: str | None
    pdp_url: str | None
    output_format: OutputFormat
    verify: bool | None
    timeout: float
    token: str | None = None
    cache_dir: str | None = None
    verbose: int = 0
