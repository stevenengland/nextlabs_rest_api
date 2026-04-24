from __future__ import annotations

import threading
import time
from collections.abc import Awaitable, Generator
from typing import Callable

import httpx

from nextlabs_sdk._auth._refresh_token_policy import RefreshDecision, decide
from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._null_token_cache import NullTokenCache
from nextlabs_sdk._auth._token_cache._token_cache import TokenCache
from nextlabs_sdk._json_response import decode_json_object, require_int, require_str
from nextlabs_sdk._logging import logger
from nextlabs_sdk.exceptions import AuthenticationError, RefreshTokenExpiredError

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

_MSG_LIFETIME_EXCEEDED = "Refresh token lifetime exceeded — re-login required. {hint}"
_MSG_SERVER_REJECTED = "Refresh token rejected by server — re-login required. {hint}"
_MSG_NO_CREDS = "No refresh token and no password available. {hint}"

_RESPONSE_BODY_PREVIEW_LIMIT = 2000


def _wall_to_monotonic(wall_expires_at: float) -> float:
    """Translate an absolute wall-clock expiry into a monotonic deadline.

    In-memory expiry checks use ``time.monotonic()`` so NTP steps or
    manual clock adjustments cannot flip a token's validity. Persisted
    cache entries still store wall-clock ``expires_at`` because
    monotonic clocks don't survive a process restart; callers translate
    them to a local monotonic deadline on load and after each refresh.
    """
    return time.monotonic() + (wall_expires_at - time.time())


def _truncate_body(text: str, total_bytes: int) -> str:
    if len(text) <= _RESPONSE_BODY_PREVIEW_LIMIT:
        return text
    suffix = f"… (truncated, {total_bytes} bytes total)"
    if len(suffix) >= _RESPONSE_BODY_PREVIEW_LIMIT:
        return suffix[:_RESPONSE_BODY_PREVIEW_LIMIT]
    return f"{text[: _RESPONSE_BODY_PREVIEW_LIMIT - len(suffix)]}{suffix}"


def _refresh_failure_details(
    response: httpx.Response | None,
) -> tuple[int | None, str | None]:
    if response is None:
        return None, None
    try:
        body = response.text
    except Exception:  # pragma: no cover - httpx decoding edge case
        body = ""
    try:
        total_bytes = len(response.content)
    except Exception:  # pragma: no cover - httpx content access edge case
        total_bytes = len(body.encode("utf-8"))
    return response.status_code, _truncate_body(body, total_bytes)


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


def _build_password_request(
    *,
    token_url: str,
    username: str,
    password: str | None,
    client_id: str,
) -> httpx.Request:
    return httpx.Request(
        method=_HTTP_POST,
        url=token_url,
        data={
            "grant_type": "password",
            "username": username,
            "password": password,
            "client_id": client_id,
        },
        headers=_form_headers(),
    )


def _build_refresh_request(
    *,
    token_url: str,
    refresh_token: str,
    client_id: str,
) -> httpx.Request:
    return httpx.Request(
        method=_HTTP_POST,
        url=token_url,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
        },
        headers=_form_headers(),
    )


def _raise_unless_password_available(
    *,
    password: str | None,
    token_url: str,
    message: str,
    exc_cls: type[AuthenticationError],
    warn: str | None,
) -> None:
    if password is not None:
        return
    if warn is not None:
        logger.warning(warn)
    raise exc_cls(
        message.format(hint=_RELOGIN_HINT),
        status_code=None,
        response_body=None,
        request_method=_HTTP_POST,
        request_url=token_url,
    )


def _raise_server_rejected_refresh(
    *,
    password: str | None,
    token_url: str,
    refresh_response: httpx.Response | None,
) -> None:
    if password is not None:
        return
    logger.warning(
        "cloudaz auth: refresh token rejected by server"
        " and no password available — re-login required",
    )
    status_code, response_body = _refresh_failure_details(refresh_response)
    raise RefreshTokenExpiredError(
        _MSG_SERVER_REJECTED.format(hint=_RELOGIN_HINT),
        status_code=status_code,
        response_body=response_body,
        request_method=_HTTP_POST,
        request_url=token_url,
    )


def _handle_refresh_failure(
    *,
    decision: RefreshDecision,
    password: str | None,
    token_url: str,
    refresh_response: httpx.Response | None = None,
) -> None:
    if decision is RefreshDecision.USE_REFRESH:
        _raise_server_rejected_refresh(
            password=password,
            token_url=token_url,
            refresh_response=refresh_response,
        )
    elif decision is RefreshDecision.KNOWN_EXPIRED:
        logger.debug("cloudaz auth: refresh skipped (known-expired)")
        _raise_unless_password_available(
            password=password,
            token_url=token_url,
            message=_MSG_LIFETIME_EXCEEDED,
            exc_cls=RefreshTokenExpiredError,
            warn="cloudaz auth: refresh token expired"
            " and no password available — re-login required",
        )
    else:
        _raise_unless_password_available(
            password=password,
            token_url=token_url,
            message=_MSG_NO_CREDS,
            exc_cls=AuthenticationError,
            warn=None,
        )


class CloudAzAuth(httpx.Auth):
    """OIDC password grant auth for the CloudAz Console API.

    The OIDC token endpoint returns both ``access_token`` and, in some
    deployments, ``id_token``. CloudAzAuth sends ``access_token`` in
    the ``Authorization: Bearer …`` header: the Reporter microservice
    under the same ``base_url`` rejects ``id_token`` with HTTP 403 and
    accepts only ``access_token``, and the Console endpoints accept
    either. This matches NextLabs' own developer portal "Try it out"
    guidance, which documents pasting the ``access_token`` (prefixed
    ``AT-``) as the bearer credential. Any ``id_token`` the server
    returns is persisted to the cache for forward compatibility but
    ignored for authentication.

    Supports an optional pluggable :class:`TokenCache` backend. Expiry is
    tracked as absolute UTC epoch seconds so that cached tokens survive
    process restarts.

    When ``refresh_token_lifetime`` is provided, the SDK records the
    refresh token's absolute expiry at every successful token
    acquisition and uses it to short-circuit re-auth once the lifetime
    has elapsed — skipping a doomed HTTP round-trip and surfacing a
    :class:`RefreshTokenExpiredError` (or falling back to the password
    grant when a password is configured).
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
        self._cache_key = f"{token_url}|{username}|{client_id}|cloudaz"
        self._lock = threading.Lock()
        self.refresh_token_lifetime: int | None = None

        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._refresh_expires_at: float | None = None
        self._expires_at: float = _INITIAL_EXPIRY_AT

        cached = self._cache.load(self._cache_key)
        if cached is not None:
            self._refresh_token = cached.refresh_token
            if cached.refresh_expires_at is not None:
                self._refresh_expires_at = _wall_to_monotonic(
                    cached.refresh_expires_at,
                )
            if not cached.is_expired(
                now=time.time(),
                safety_margin=_EXPIRY_SAFETY_MARGIN,
            ):
                self._access_token = cached.access_token
                self._expires_at = _wall_to_monotonic(cached.expires_at)

    def auth_flow(
        self,
        request: httpx.Request,
    ) -> Generator[httpx.Request, httpx.Response, None]:
        if not self._has_valid_token():
            yield from self._reauthenticate()

        request.headers["Authorization"] = f"Bearer {self._access_token}"
        response = yield request

        if response.status_code == _UNAUTHORIZED_STATUS or _is_spa_redirect(response):
            yield from self._reauthenticate()
            request.headers["Authorization"] = f"Bearer {self._access_token}"
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
        token without making a password HTTP call. No-op when a valid token
        is already available in memory.
        """
        if self._has_valid_token():
            return
        if self._try_refresh_sync(send):
            return
        logger.debug("cloudaz auth: falling back to password grant")
        response = send(
            _build_password_request(
                token_url=self._token_url,
                username=self._username,
                password=self._password,
                client_id=self._client_id,
            ),
        )
        self._parse_token_response(response)

    async def ensure_token_async(
        self,
        send: Callable[[httpx.Request], Awaitable[httpx.Response]],
    ) -> None:
        """Async counterpart of :meth:`ensure_token`."""
        if self._has_valid_token():
            return
        if await self._try_refresh_async(send):
            return
        logger.debug("cloudaz auth: falling back to password grant")
        response = await send(
            _build_password_request(
                token_url=self._token_url,
                username=self._username,
                password=self._password,
                client_id=self._client_id,
            ),
        )
        self._parse_token_response(response)

    def _refresh_decision(self) -> RefreshDecision:
        if self._refresh_token is None:
            return RefreshDecision.ABSENT
        return decide(
            refresh_token=self._refresh_token,
            refresh_expires_at=self._refresh_expires_at,
            now=time.monotonic(),
        )

    def _has_valid_token(self) -> bool:
        with self._lock:
            return (
                self._access_token is not None and time.monotonic() < self._expires_at
            )

    def _reauthenticate(self) -> Generator[httpx.Request, httpx.Response, None]:
        decision = self._refresh_decision()
        if decision is RefreshDecision.USE_REFRESH:
            logger.debug("cloudaz auth: refresh attempt starting")
            assert self._refresh_token is not None
            response = yield _build_refresh_request(
                token_url=self._token_url,
                refresh_token=self._refresh_token,
                client_id=self._client_id,
            )
            if response.status_code == _OK_STATUS:
                self._parse_token_response(response)
                logger.debug("cloudaz auth: refresh succeeded")
                return
            _handle_refresh_failure(
                decision=decision,
                password=self._password,
                token_url=self._token_url,
                refresh_response=response,
            )
        else:
            _handle_refresh_failure(
                decision=decision, password=self._password, token_url=self._token_url
            )

        logger.debug("cloudaz auth: falling back to password grant")
        response = yield _build_password_request(
            token_url=self._token_url,
            username=self._username,
            password=self._password,
            client_id=self._client_id,
        )
        self._parse_token_response(response)

    def _try_refresh_sync(
        self,
        send: Callable[[httpx.Request], httpx.Response],
    ) -> bool:
        decision = self._refresh_decision()
        refresh_response: httpx.Response | None = None
        if decision is RefreshDecision.USE_REFRESH:
            logger.debug("cloudaz auth: refresh attempt starting")
            assert self._refresh_token is not None
            refresh_response = send(
                _build_refresh_request(
                    token_url=self._token_url,
                    refresh_token=self._refresh_token,
                    client_id=self._client_id,
                ),
            )
            if refresh_response.status_code == _OK_STATUS:
                self._parse_token_response(refresh_response)
                logger.debug("cloudaz auth: refresh succeeded")
                return True
        _handle_refresh_failure(
            decision=decision,
            password=self._password,
            token_url=self._token_url,
            refresh_response=refresh_response,
        )
        return False

    async def _try_refresh_async(
        self,
        send: Callable[[httpx.Request], Awaitable[httpx.Response]],
    ) -> bool:
        decision = self._refresh_decision()
        refresh_response: httpx.Response | None = None
        if decision is RefreshDecision.USE_REFRESH:
            logger.debug("cloudaz auth: refresh attempt starting")
            assert self._refresh_token is not None
            refresh_response = await send(
                _build_refresh_request(
                    token_url=self._token_url,
                    refresh_token=self._refresh_token,
                    client_id=self._client_id,
                ),
            )
            if refresh_response.status_code == _OK_STATUS:
                self._parse_token_response(refresh_response)
                logger.debug("cloudaz auth: refresh succeeded")
                return True
        _handle_refresh_failure(
            decision=decision,
            password=self._password,
            token_url=self._token_url,
            refresh_response=refresh_response,
        )
        return False

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
        now_wall = time.time()
        now_mono = time.monotonic()
        expires_at = now_wall + expires_in - _EXPIRY_SAFETY_MARGIN
        mono_expires_at = now_mono + expires_in - _EXPIRY_SAFETY_MARGIN
        access_token = require_str(
            body,
            "access_token",
            error_cls=AuthenticationError,
            context=" in token response",
        )
        id_token_raw = body.get("id_token")
        id_token = id_token_raw if isinstance(id_token_raw, str) else None
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
        refresh_expires_at = (
            None
            if self.refresh_token_lifetime is None
            else now_wall + self.refresh_token_lifetime
        )
        mono_refresh_expires_at = (
            None
            if self.refresh_token_lifetime is None
            else now_mono + self.refresh_token_lifetime
        )

        with self._lock:
            self._access_token = access_token
            self._refresh_token = refresh_token
            self._expires_at = mono_expires_at
            self._refresh_expires_at = mono_refresh_expires_at

        self._cache.save(
            self._cache_key,
            CachedToken(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                token_type=token_type,
                scope=scope,
                id_token=id_token,
                refresh_expires_at=refresh_expires_at,
            ),
        )
