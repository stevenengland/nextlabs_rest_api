"""Verify the file-backed token cache survives CLI invocations.

Runs ``nextlabs auth login`` in a subprocess with an isolated
``NEXTLABS_CACHE_DIR`` pointing at ``tmp_path``, asserts the cache file
materialized, then runs ``nextlabs auth status`` and checks that no
second OIDC token request hit WireMock.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import httpx
import pytest

_OIDC_PATH = "/cas/oidc/accessToken"


@pytest.fixture
def oidc_stub(seeded_wiremock: str) -> str:
    """Register a password-grant stub on ``/cas/oidc/accessToken``."""
    mapping = {
        "priority": 1,
        "request": {"method": "POST", "urlPath": _OIDC_PATH},
        "response": {
            "status": 200,
            "headers": {"Content-Type": "application/json"},
            "jsonBody": {
                "access_token": "at-e2e-1",
                "id_token": "id-e2e-1",
                "refresh_token": "rt-e2e-1",
                "token_type": "bearer",
                "expires_in": 3600,
                "scope": "",
            },
        },
    }
    httpx.post(f"{seeded_wiremock}/__admin/mappings", json=mapping, timeout=5.0)
    httpx.post(f"{seeded_wiremock}/__admin/requests/reset", timeout=5.0)
    return seeded_wiremock


def _oidc_call_count(base_url: str) -> int:
    payload = {"method": "POST", "url": _OIDC_PATH}
    response = httpx.post(
        f"{base_url}/__admin/requests/count",
        json=payload,
        timeout=5.0,
    )
    response.raise_for_status()
    return int(response.json()["count"])


def _run_cli(
    base_url: str,
    cache_path: Path,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    for proxy_var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env.pop(proxy_var, None)
    env["NEXTLABS_BASE_URL"] = base_url
    env["NEXTLABS_USERNAME"] = "alice"
    env["NEXTLABS_PASSWORD"] = "pw"
    env["NEXTLABS_CACHE_DIR"] = str(cache_path)
    # A pre-issued token would bypass login + cache; make sure it's unset.
    env.pop("NEXTLABS_TOKEN", None)
    return subprocess.run(
        ["nextlabs", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )


def test_login_then_reuse_cached_token(
    oidc_stub: str,
    tmp_path: Path,
) -> None:
    cache_file = tmp_path / "tokens.json"
    login = _run_cli(oidc_stub, cache_file, "auth", "login")
    assert login.returncode == 0, login.stderr

    assert cache_file.exists(), f"expected cache at {cache_file}"
    cache_payload = json.loads(cache_file.read_text())
    assert cache_payload, "cache file should contain at least one entry"

    assert _oidc_call_count(oidc_stub) == 1

    # Second invocation: ``auth status`` reads the cache directly and
    # must not re-hit the OIDC endpoint.
    status = _run_cli(oidc_stub, cache_file, "auth", "status")
    assert status.returncode == 0, status.stderr
    assert "valid" in status.stdout.lower()

    assert _oidc_call_count(oidc_stub) == 1
