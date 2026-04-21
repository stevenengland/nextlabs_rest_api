from __future__ import annotations

_CLOUDAZ_TOKEN_PATH = "/cas/token"
_PDP_TOKEN_PATH = "/dpc/oauth"


def resolve_pdp_token_url(
    *,
    base_url: str,
    auth_base_url: str | None,
    token_url: str | None,
) -> str:
    """Return the OAuth token URL for a PDP client.

    Precedence (first match wins):

    1. ``token_url`` — used verbatim.
    2. ``auth_base_url`` — ``{auth_base_url}/cas/token`` (CloudAz host).
    3. Otherwise — ``{base_url}/dpc/oauth`` (PDP host).

    Trailing slashes on ``base_url`` / ``auth_base_url`` are stripped
    before path composition; ``token_url`` is returned verbatim.

    Args:
        base_url: PDP API host.
        auth_base_url: Optional CloudAz host hosting ``/cas/token``.
        token_url: Optional full token URL; if set, wins over everything.

    Returns:
        The resolved OAuth token URL.
    """
    if token_url:
        return token_url
    if auth_base_url:
        return f"{auth_base_url.rstrip('/')}{_CLOUDAZ_TOKEN_PATH}"
    return f"{base_url.rstrip('/')}{_PDP_TOKEN_PATH}"
