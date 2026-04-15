from __future__ import annotations

import threading
import time
from collections.abc import Generator

import httpx

from nextlabs_sdk.exceptions import AuthenticationError

_EXPIRY_SAFETY_MARGIN = 60
_OK_STATUS = 200
_UNAUTHORIZED_STATUS = 401


class CloudAzAuth(httpx.Auth):
    """OIDC password grant auth for the CloudAz Console API."""

    requires_request_body = False
    requires_response_body = True

    def __init__(
        self,
        token_url: str,
        username: str,
        password: str,
        client_id: str,
    ) -> None:
        self._token_url = token_url
        self._username = username
        self._password = password
        self._client_id = client_id
        self._token: str | None = None
        self._token_expiry: float = 0
        self._lock = threading.Lock()

    def auth_flow(
        self,
        request: httpx.Request,
    ) -> Generator[httpx.Request, httpx.Response, None]:
        if not self._has_valid_token():
            token_response = yield self._build_token_request()
            self._parse_token_response(token_response)

        request.headers["Authorization"] = f"Bearer {self._token}"
        response = yield request

        if response.status_code == _UNAUTHORIZED_STATUS:
            token_response = yield self._build_token_request()
            self._parse_token_response(token_response)
            request.headers["Authorization"] = f"Bearer {self._token}"
            yield request

    def _has_valid_token(self) -> bool:
        with self._lock:
            return self._token is not None and time.monotonic() < self._token_expiry

    def _build_token_request(self) -> httpx.Request:
        return httpx.Request(
            method="POST",
            url=self._token_url,
            data={
                "grant_type": "password",
                "username": self._username,
                "password": self._password,
                "client_id": self._client_id,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    def _parse_token_response(
        self,
        response: httpx.Response,
    ) -> None:
        if response.status_code != _OK_STATUS:
            raise AuthenticationError(
                f"Token acquisition failed: HTTP {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
                request_method="POST",
                request_url=self._token_url,
            )

        body = response.json()
        with self._lock:
            self._token = body["id_token"]
            expires_in = int(body["expires_in"])
            self._token_expiry = time.monotonic() + expires_in - _EXPIRY_SAFETY_MARGIN
