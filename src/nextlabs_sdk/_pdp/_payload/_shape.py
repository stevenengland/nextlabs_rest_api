"""Raw-XACML shape detection for loaded payload dicts."""

from __future__ import annotations

from nextlabs_sdk.exceptions import PdpPayloadError


def is_raw_xacml(payload: dict[str, object]) -> bool:
    """Return ``True`` when ``payload`` has the raw XACML top-level shape.

    Specifically, ``payload["Request"]`` must be an object and
    ``payload["Request"]["Category"]`` must be a list.
    """
    request = payload.get("Request")
    if not isinstance(request, dict):
        return False
    return isinstance(request.get("Category"), list)


def require_raw_xacml(payload: dict[str, object]) -> dict[str, object]:
    """Validate that ``payload`` is raw XACML-shaped; raise otherwise."""
    request = payload.get("Request")
    if not isinstance(request, dict):
        raise PdpPayloadError(
            "Raw XACML payload missing top-level 'Request' object",
        )
    if not isinstance(request.get("Category"), list):
        raise PdpPayloadError(
            "Raw XACML payload 'Request.Category' must be a list",
        )
    return payload
