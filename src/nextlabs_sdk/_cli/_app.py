from __future__ import annotations

import typer

from nextlabs_sdk._cli._auth_cmd import auth_app
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._tags_cmd import tags_app

app = typer.Typer(
    name="nextlabs",
    help="NextLabs CloudAz SDK CLI",
    invoke_without_command=True,
)

app.add_typer(auth_app, name="auth")
app.add_typer(tags_app, name="tags")


@app.callback()
def main(
    ctx: typer.Context,
    base_url: str | None = typer.Option(
        None,
        envvar="NEXTLABS_BASE_URL",
        help="CloudAz base URL",
    ),
    username: str | None = typer.Option(
        None,
        envvar="NEXTLABS_USERNAME",
        help="CloudAz username",
    ),
    password: str | None = typer.Option(
        None,
        envvar="NEXTLABS_PASSWORD",
        help="CloudAz password",
    ),
    client_id: str = typer.Option(
        "ControlCenterOIDCClient",
        envvar="NEXTLABS_CLIENT_ID",
        help="OIDC client ID",
    ),
    client_secret: str | None = typer.Option(
        None,
        envvar="NEXTLABS_CLIENT_SECRET",
        help="PDP client secret",
    ),
    pdp_url: str | None = typer.Option(
        None,
        envvar="NEXTLABS_PDP_URL",
        help="PDP base URL (defaults to --base-url)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output JSON instead of Rich tables",
    ),
    no_verify: bool = typer.Option(
        False,
        "--no-verify",
        help="Disable SSL certificate verification",
    ),
    timeout: float = typer.Option(
        30.0,
        help="Request timeout in seconds",
    ),
) -> None:
    """NextLabs CloudAz SDK CLI."""
    ctx.obj = CliContext(
        base_url=base_url,
        username=username,
        password=password,
        client_id=client_id,
        client_secret=client_secret,
        pdp_url=pdp_url,
        json_output=json_output,
        no_verify=no_verify,
        timeout=timeout,
    )
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
