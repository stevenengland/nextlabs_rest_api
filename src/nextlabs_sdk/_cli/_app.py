from __future__ import annotations

import typer

from nextlabs_sdk._cli._activity_logs_cmd import activity_logs_app
from nextlabs_sdk._cli._audit_logs_cmd import audit_logs_app
from nextlabs_sdk._cli._auth_cmd import auth_app
from nextlabs_sdk._cli._component_types_cmd import component_types_app
from nextlabs_sdk._cli._components_cmd import components_app
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._dashboard_cmd import dashboard_app
from nextlabs_sdk._cli._logging_setup import configure_cli_logging
from nextlabs_sdk._cli._operators_cmd import operators_app
from nextlabs_sdk._cli._output_format import OutputFormat
from nextlabs_sdk._cli._pdp_auth_source import PdpAuthSource
from nextlabs_sdk._cli._pdp_cmd import pdp_app
from nextlabs_sdk._cli._policies_cmd import policies_app
from nextlabs_sdk._cli._reports_cmd import reports_app
from nextlabs_sdk._cli._reporter_audit_logs_cmd import reporter_audit_logs_app
from nextlabs_sdk._cli._system_config_cmd import system_config_app
from nextlabs_sdk._cli._tags_cmd import tags_app

_DEFAULT_TIMEOUT_SECONDS = 30.0

app = typer.Typer(
    name="nextlabs",
    help="NextLabs CloudAz SDK CLI",
    invoke_without_command=True,
)

app.add_typer(audit_logs_app, name="audit-logs")
app.add_typer(activity_logs_app, name="activity-logs")
app.add_typer(auth_app, name="auth")
app.add_typer(component_types_app, name="component-types")
app.add_typer(components_app, name="components")
app.add_typer(dashboard_app, name="dashboard")
app.add_typer(operators_app, name="operators")
app.add_typer(pdp_app, name="pdp")
app.add_typer(policies_app, name="policies")
app.add_typer(reports_app, name="reports")
app.add_typer(reporter_audit_logs_app, name="reporter-audit-logs")
app.add_typer(system_config_app, name="system-config")
app.add_typer(tags_app, name="tags")


@app.callback()
def main(
    ctx: typer.Context,
    base_url: str | None = typer.Option(
        None,
        envvar="NEXTLABS_BASE_URL",
        help="CloudAz base URL (host serving /cas/token).",
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
        help="PDP base URL (host serving /dpc/authorization/*).",
    ),
    pdp_auth: PdpAuthSource | None = typer.Option(
        None,
        "--pdp-auth",
        envvar="NEXTLABS_PDP_AUTH",
        case_sensitive=False,
        help=(
            "Token endpoint PDP commands should use: 'cloudaz' "
            "(/cas/token on the CloudAz host) or 'pdp' (/dpc/oauth on "
            "the PDP host). Defaults to 'cloudaz' when --base-url is "
            "set, else 'pdp'."
        ),
    ),
    output: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "-o",
        "--output",
        case_sensitive=False,
        help=(
            "Output format: table (default compact), wide (extra columns), "
            "detail (sectioned per-item), json (raw JSON)."
        ),
    ),
    verify: bool | None = typer.Option(
        None,
        "--verify/--no-verify",
        help=(
            "Enable or disable SSL certificate verification for this "
            "invocation. When omitted, the persisted per-account preference "
            "is used (default: verify)."
        ),
    ),
    timeout: float = typer.Option(
        _DEFAULT_TIMEOUT_SECONDS,
        help="Request timeout in seconds",
    ),
    token: str | None = typer.Option(
        None,
        envvar="NEXTLABS_TOKEN",
        help="Pre-issued bearer token; bypasses login and token cache.",
    ),
    cache_dir: str | None = typer.Option(
        None,
        envvar="NEXTLABS_CACHE_DIR",
        help="Override the token cache directory.",
    ),
    verbose: int = typer.Option(
        0,
        "-v",
        "--verbose",
        count=True,
        help=(
            "Increase verbosity. -v: show request context on errors; "
            "-vv: trace every HTTP request/response."
        ),
    ),
) -> None:
    """NextLabs CloudAz SDK CLI."""
    configure_cli_logging(verbose)
    ctx.obj = CliContext(
        base_url=base_url,
        username=username,
        password=password,
        client_id=client_id,
        client_secret=client_secret,
        pdp_url=pdp_url,
        output_format=output,
        verify=verify,
        timeout=timeout,
        token=token,
        cache_dir=cache_dir,
        verbose=verbose,
        pdp_auth=pdp_auth,
    )
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
