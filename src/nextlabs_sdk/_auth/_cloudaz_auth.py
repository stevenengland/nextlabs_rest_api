from __future__ import annotations

import threading
import time
from collections.abc import Awaitable, Generator
from typing import Callable

import httpx

from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._null_token_cache import NullTokenCache
from nextlabs_sdk._auth._token_cache._token_cache import TokenCache
from nextlabs_sdk._json_response import decode_json_object, require_int, require_str
from nextlabs_sdk.exceptions import AuthenticationError

_EXPIRY_SAFETY_MARGIN = 60
_OK_STATUS = 200
_UNAUTHORIZED_STATUS = 401
_REDIRECT_MIN_STATUS = 300
_REDIRECT_MAX_STATUS = 399
_SPA_FRAGMENT = "#"
_LOCATION_HEADER = "location"
_RELOGIN_HINT = "Run `nextlabs auth login` to re-authenticate."
_SPA_REDIRECT_MSG = (
    "Server redirected API call to SPA login page "
    "(Location={location!r}) — access token was rejected. {hint}"
)
_HTTP_POST = "POST"
_FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"
_INITIAL_EXPIRY_AT = float(0)


def _spa_redirect_location(response: httpx.Response) -> str:
    for hop in response.history:
        location = hop.headers.get(_LOCATION_HEADER, "")
        if _SPA_FRAGMENT in location:
            return location
    return response.headers.get(_LOCATION_HEADER, "")


def _is_spa_redirect(response: httpx.Response) -> bool:
    for hop in response.history:
        if _SPA_FRAGMENT in hop.headers.get(_LOCATION_HEADER, ""):
            return True
    status = response.status_code
    if _REDIRECT_MIN_STATUS <= status <= _REDIRECT_MAX_STATUS:
        return _SPA_FRAGMENT in response.headers.get(_LOCATION_HEADER, "")
    return False


def _form_headers() -> dict[str, str]:
    return {"Content-Type": _FORM_CONTENT_TYPE}


class CloudAzAuth(httpx.Auth):
    """OIDC password grant auth for the CloudAz Console API.

    Supports an optional pluggable :class:`TokenCache` backend. Expiry is
    tracked as absolute UTC epoch seconds so that cached tokens survive
    process restarts.
    """

    requires_request_body = False
    requires_response_body = True

    def __init__(
        self,
        token_url: str,
        username: str,
        password: str | None,
        client_id: str,
        *,
        token_cache: TokenCache | None = None,
    ) -> None:
        self._token_url = token_url
        self._username = username
        self._password = password
        self._client_id = client_id
        self._cache: TokenCache = token_cache or NullTokenCache()
        self._cache_key = f"{token_url}|{username}|{client_id}"
        self._lock = threading.Lock()

        self._token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float = _INITIAL_EXPIRY_AT

        cached = self._cache.load(self._cache_key)
        if cached is not None:
            self._refresh_token = cached.refresh_token
            if not cached.is_expired(
                now=time.time(),
                safety_margin=_EXPIRY_SAFETY_MARGIN,
            ):
                self._token = cached.access_token
                self._expires_at = cached.expires_at

    def auth_flow(
        self,
        request: httpx.Request,
    ) -> Generator[httpx.Request, httpx.Response, None]:
        if not self._has_valid_token():
            yield from self._reauthenticate()

        request.headers["Authorization"] = f"Bearer {self._token}"
        response = yield request

        if response.status_code == _UNAUTHORIZED_STATUS or _is_spa_redirect(response):
            yield from self._reauthenticate()
            request.headers["Authorization"] = f"Bearer {self._token}"
            retried = yield request
            if _is_spa_redirect(retried):
                raise AuthenticationError(
                    _SPA_REDIRECT_MSG.format(
                        location=_spa_redirect_location(retried),
                        hint=_RELOGIN_HINT,
                    ),
                    status_code=retried.status_code,
                    response_body=None,
                    request_method=request.method,
                    request_url=str(request.url),
                )

    def ensure_token(
        self,
        send: Callable[[httpx.Request], httpx.Response],
    ) -> None:
        """Fetch and cache a token synchronously via a provided transport.

        Intended for explicit `authenticate()` flows that need to acquire a
        token without making a business API call. No-op when a valid token is
        already available in memory.
        """
        if self._has_valid_token():
            return
        if self._refresh_token is not None:
            response = send(self._build_refresh_request(self._refresh_token))
            if response.status_code == _OK_STATUS:
                self._parse_token_response(response)
                return
        if self._password is None:
            raise AuthenticationError(
                f"Token expired and no refresh available. {_RELOGIN_HINT}",
                status_code=None,
                response_body=None,
                request_method=_HTTP_POST,
                request_url=self._token_url,
            )
        response = send(self._build_password_request())
        self._parse_token_response(response)

    async def ensure_token_async(
        self,
        send: Callable[[httpx.Request], Awaitable[httpx.Response]],
    ) -> None:
        """Async counterpart of :meth:`ensure_token`."""
        if self._has_valid_token():
            return
        if self._refresh_token is not None:
            response = await send(self._build_refresh_request(self._refresh_token))
            if response.status_code == _OK_STATUS:
                self._parse_token_response(response)
                return
        if self._password is None:
            raise AuthenticationError(
                f"Token expired and no refresh available. {_RELOGIN_HINT}",
                status_code=None,
                response_body=None,
                request_method=_HTTP_POST,
                request_url=self._token_url,
            )
        response = await send(self._build_password_request())
        self._parse_token_response(response)

    def _has_valid_token(self) -> bool:
        with self._lock:
            return self._token is not None and time.time() < self._expires_at

    def _reauthenticate(self) -> Generator[httpx.Request, httpx.Response, None]:
        if self._refresh_token is not None:
            response = yield self._build_refresh_request(self._refresh_token)
            if response.status_code == _OK_STATUS:
                self._parse_token_response(response)
                return

        if self._password is None:
            raise AuthenticationError(
                f"Token expired and no refresh available. {_RELOGIN_HINT}",
                status_code=None,
                response_body=None,
                request_method=_HTTP_POST,
                request_url=self._token_url,
            )

        response = yield self._build_password_request()
        self._parse_token_response(response)

    def _build_password_request(self) -> httpx.Request:
        return httpx.Request(
            method=_HTTP_POST,
            url=self._token_url,
            data={
                "grant_type": "password",
                "username": self._username,
                "password": self._password,
                "client_id": self._client_id,
            },
            headers=_form_headers(),
        )

    def _build_refresh_request(self, refresh_token: str) -> httpx.Request:
        return httpx.Request(
            method=_HTTP_POST,
            url=self._token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self._client_id,
            },
            headers=_form_headers(),
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
                request_method=_HTTP_POST,
                request_url=self._token_url,
            )

        body = decode_json_object(
            response,
            error_cls=AuthenticationError,
            context=" in token response",
        )
        expires_in = require_int(
            body,
            "expires_in",
            error_cls=AuthenticationError,
            context=" in token response",
        )
        now = time.time()
        expires_at = now + expires_in - _EXPIRY_SAFETY_MARGIN
        access_token = require_str(
            body,
            "access_token",
            error_cls=AuthenticationError,
            context=" in token response",
        )
        refresh_token_raw = body.get("refresh_token")
        refresh_token = (
            refresh_token_raw
            if isinstance(refresh_token_raw, str)
            else self._refresh_token
        )
        token_type_raw = body.get("token_type", "bearer")
        token_type = token_type_raw if isinstance(token_type_raw, str) else "bearer"
        scope_raw = body.get("scope")
        scope = scope_raw if isinstance(scope_raw, str) else None

        with self._lock:
            self._token = access_token
            self._refresh_token = refresh_token
            self._expires_at = expires_at

        self._cache.save(
            self._cache_key,
            CachedToken(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                token_type=token_type,
                scope=scope,
            ),
        )
