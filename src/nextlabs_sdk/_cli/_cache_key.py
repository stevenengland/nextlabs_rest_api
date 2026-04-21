from __future__ import annotations

from typing import Protocol

_TOKEN_PATH_SUFFIX = "/cas/oidc/accessToken"
_KIND_CLOUDAZ = "cloudaz"
_KIND_PDP = "pdp"
_VALID_KINDS = (_KIND_CLOUDAZ, _KIND_PDP)


class _AccountKeyFields(Protocol):
    @property
    def base_url(self) -> str: ...
    @property
    def username(self) -> str: ...
    @property
    def client_id(self) -> str: ...
    @property
    def kind(self) -> str: ...


def cache_key_for(account: _AccountKeyFields) -> str:
    """Build the token-cache key for an account.

    Single source of truth for the 4-segment cache-key format
    ``<url>|<username>|<client_id>|<kind>``. The URL segment includes
    the CloudAz OIDC path suffix for ``kind="cloudaz"`` entries and is
    the raw base URL for ``kind="pdp"`` entries. Accepts any object
    exposing ``base_url``, ``username``, ``client_id``, and ``kind``.
    """
    if account.kind == _KIND_PDP:
        url_segment = account.base_url
    else:
        url_segment = f"{account.base_url}{_TOKEN_PATH_SUFFIX}"
    return f"{url_segment}|{account.username}|{account.client_id}|{account.kind}"


def parse_cache_key(key: str) -> tuple[str, str, str, str] | None:
    """Parse a token-cache key into ``(base_url, username, client_id, kind)``.

    Accepts both the new 4-segment format and the legacy 3-segment
    CloudAz format; legacy keys resolve to ``kind="cloudaz"`` so users
    upgrading from pre-#58 caches do not lose their session. Returns
    ``None`` when the key does not match either format.
    """
    parts = key.split("|")
    if len(parts) == 4:
        return _parse_four_segment(parts)
    if len(parts) == 3:
        return _parse_legacy_three_segment(parts)
    return None


def _parse_four_segment(parts: list[str]) -> tuple[str, str, str, str] | None:
    url_part, username, client_id, kind = parts
    if kind not in _VALID_KINDS or not (url_part and client_id):
        return None
    if kind == _KIND_PDP:
        return url_part, username, client_id, kind
    if not url_part.endswith(_TOKEN_PATH_SUFFIX) or not username:
        return None
    base_url = url_part[: -len(_TOKEN_PATH_SUFFIX)]
    if not base_url:
        return None
    return base_url, username, client_id, kind


def _parse_legacy_three_segment(parts: list[str]) -> tuple[str, str, str, str] | None:
    base_part, username, client_id = parts
    if not base_part.endswith(_TOKEN_PATH_SUFFIX):
        return None
    base_url = base_part[: -len(_TOKEN_PATH_SUFFIX)]
    if not (base_url and username and client_id):
        return None
    return base_url, username, client_id, _KIND_CLOUDAZ
