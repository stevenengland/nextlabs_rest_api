"""Small E2E helpers."""

from __future__ import annotations

from collections.abc import Generator

import httpx


class StaticBearer(httpx.Auth):
    """httpx.Auth that injects a fixed bearer token.

    Used to bypass the real OIDC flow in E2E tests. The SDK's public
    clients accept an ``auth`` override precisely for this purpose.
    """

    def __init__(self, token: str) -> None:
        self._token = token

    def auth_flow(
        self,
        request: httpx.Request,
    ) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request


def register_pdp_token_stub(base_url: str, token: str) -> None:
    """Seed WireMock with a ``/cas/token`` stub returning a fake OAuth token."""
    body = {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    mapping = {
        "request": {"method": "POST", "urlPathPattern": "/cas/token"},
        "response": {
            "status": 200,
            "headers": {"Content-Type": "application/json"},
            "jsonBody": body,
        },
    }
    httpx.post(f"{base_url}/__admin/mappings", json=mapping, timeout=5.0)
