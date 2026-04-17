from __future__ import annotations

from collections.abc import Generator

import httpx


class StaticTokenAuth(httpx.Auth):
    """Send a static bearer token; no refresh, no cache, no network."""

    def __init__(self, token: str) -> None:
        self._token = token

    def auth_flow(
        self,
        request: httpx.Request,
    ) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request
