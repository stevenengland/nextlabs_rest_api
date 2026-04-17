from __future__ import annotations

import httpx

from nextlabs_sdk._auth._static_token_auth import StaticTokenAuth


def test_adds_bearer_header_without_network() -> None:
    auth = StaticTokenAuth(token="T")
    request = httpx.Request("GET", "https://example.com/api")

    flow = auth.auth_flow(request)
    api_request = next(flow)

    assert api_request.headers["Authorization"] == "Bearer T"
