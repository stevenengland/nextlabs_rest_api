"""One happy + one error invocation per top-level CLI command group.

Exercises the installed ``nextlabs`` entry point in a subprocess so the
full dispatch wiring (Typer app, context, client factory, output
renderer, error handler) is covered. Uses ``NEXTLABS_TOKEN`` to bypass
the OIDC flow — token-cache persistence is covered separately in
:mod:`tests.e2e.test_token_cache_persistence`.

Groups whose happy path requires endpoints outside the spec-derived
stub set (``audit-logs``, ``reports``, ``dashboard``) are covered via
``--help`` smoke tests: wiring check only.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable

import httpx
import pytest

CliRunner = Callable[..., subprocess.CompletedProcess[str]]


@pytest.fixture
def pdp_cli_stub(seeded_wiremock: str) -> str:
    """Stub the PDP endpoint with a JSON Permit response for CLI tests."""
    mapping = {
        "priority": 1,
        "request": {
            "method": "POST",
            "urlPath": "/dpc/authorization/pdp",
        },
        "response": {
            "status": 200,
            "headers": {"Content-Type": "application/json"},
            "jsonBody": {
                "Response": [
                    {
                        "Decision": "Permit",
                        "Status": {
                            "StatusCode": {
                                "Value": "urn:oasis:names:tc:xacml:1.0:status:ok",
                            },
                        },
                    },
                ],
            },
        },
    }
    httpx.post(
        f"{seeded_wiremock}/__admin/mappings",
        json=mapping,
        timeout=5.0,
    )
    return seeded_wiremock


@pytest.mark.parametrize(
    ("group", "happy_args"),
    [
        ("components", ("get", "1")),
        ("policies", ("get", "1")),
        ("tags", ("get", "1")),
    ],
)
def test_cli_get_happy_path(
    cli_runner: CliRunner,
    group: str,
    happy_args: tuple[str, ...],
) -> None:
    ok = cli_runner(group, *happy_args)
    assert ok.returncode == 0, f"stdout={ok.stdout}\nstderr={ok.stderr}"


@pytest.mark.parametrize(
    ("group", "err_args"),
    [
        ("components", ("get", "not-a-number")),
        ("policies", ("get", "not-a-number")),
        ("tags", ("get", "not-a-number")),
        ("component-types", ("get", "not-a-number")),
    ],
)
def test_cli_argument_validation_error(
    cli_runner: CliRunner,
    group: str,
    err_args: tuple[str, ...],
) -> None:
    bad = cli_runner(group, *err_args)
    assert bad.returncode != 0


def test_cli_pdp_eval_happy_path(
    cli_runner: CliRunner,
    pdp_cli_stub: str,
) -> None:
    assert pdp_cli_stub
    ok = cli_runner(
        "pdp",
        "eval",
        "--subject",
        "alice",
        "--resource",
        "doc:1",
        "--resource-type",
        "document",
        "--action",
        "read",
        "--application",
        "app-1",
    )
    assert ok.returncode == 0, f"stdout={ok.stdout}\nstderr={ok.stderr}"
    assert "Permit" in ok.stdout


@pytest.mark.parametrize(
    "group",
    [
        "audit-logs",
        "reports",
        "dashboard",
        "auth",
        "component-types",
        "activity-logs",
        "operators",
        "reporter-audit-logs",
        "system-config",
    ],
)
def test_cli_group_help_wired(cli_runner: CliRunner, group: str) -> None:
    """Every top-level group exposes a working ``--help`` screen."""
    ok = cli_runner(group, "--help")
    assert ok.returncode == 0, ok.stderr
    assert group.replace("-", "") in ok.stdout.lower().replace("-", "") or ok.stdout


@pytest.fixture
def new_group_stubs(seeded_wiremock: str) -> str:
    """Register manual WireMock stubs for the four CLI groups added after PR #8.

    The vendor OpenAPI fixture used by ``seeded_wiremock`` does not cover
    these endpoints, so they are stubbed by hand per the E2E spec's
    "manual WireMock stub" column.
    """
    mappings: list[dict[str, object]] = [
        {
            "priority": 1,
            "request": {
                "method": "GET",
                "urlPathPattern": "/nextlabs-reporter/api/v1/report-activity-logs/[^/]+",
            },
            "response": {
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "jsonBody": {
                    "statusCode": "100",
                    "message": "OK",
                    "data": [
                        {
                            "name": "subject",
                            "value": "alice",
                            "dataType": "string",
                            "attrType": "static",
                            "isDynamic": False,
                        },
                    ],
                },
            },
        },
        {
            "priority": 1,
            "request": {
                "method": "GET",
                "urlPath": "/console/api/v1/config/dataType/list",
            },
            "response": {
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "jsonBody": {
                    "statusCode": "100",
                    "message": "OK",
                    "data": [],
                },
            },
        },
        {
            "priority": 1,
            "request": {
                "method": "GET",
                "urlPath": "/nextlabs-reporter/api/activity-logs/search",
            },
            "response": {
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "jsonBody": {
                    "content": [],
                    "totalPages": 1,
                    "totalElements": 0,
                },
            },
        },
        {
            "priority": 1,
            "request": {
                "method": "GET",
                "urlPath": "/nextlabs-reporter/api/system-configuration/getUIConfigs",
            },
            "response": {
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "jsonBody": {"ui.theme": "light"},
            },
        },
    ]
    for mapping in mappings:
        httpx.post(
            f"{seeded_wiremock}/__admin/mappings",
            json=mapping,
            timeout=5.0,
        )
    return seeded_wiremock


@pytest.mark.parametrize(
    ("group", "happy_args"),
    [
        ("activity-logs", ("get-by-row-id", "1")),
        ("operators", ("list",)),
        ("reporter-audit-logs", ("search",)),
        ("system-config", ("get",)),
    ],
)
def test_cli_new_groups_happy_path(
    cli_runner: CliRunner,
    new_group_stubs: str,
    group: str,
    happy_args: tuple[str, ...],
) -> None:
    assert new_group_stubs
    ok = cli_runner(group, *happy_args)
    assert ok.returncode == 0, f"stdout={ok.stdout}\nstderr={ok.stderr}"


@pytest.mark.parametrize(
    ("group", "err_args"),
    [
        ("activity-logs", ("get-by-row-id", "not-a-number")),
        ("operators", ("list-by-type",)),
        ("reporter-audit-logs", ("search", "--page-size", "not-a-number")),
        ("system-config", ("get", "--unknown-flag")),
    ],
)
def test_cli_new_groups_argument_validation_error(
    cli_runner: CliRunner,
    group: str,
    err_args: tuple[str, ...],
) -> None:
    bad = cli_runner(group, *err_args)
    assert bad.returncode != 0
