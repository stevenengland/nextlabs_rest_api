"""HTTP header construction for PDP REST API calls."""

from __future__ import annotations

from nextlabs_sdk._pdp._enums import ContentType

SERVICE_HEADER = "Service"
VERSION_HEADER = "Version"
CONTENT_TYPE_HEADER = "Content-Type"

DEFAULT_SERVICE = "EVAL"
DEFAULT_VERSION = "1.0"


def build_pdp_headers(
    content_type: ContentType,
    *,
    service: str = DEFAULT_SERVICE,
    version: str = DEFAULT_VERSION,
) -> dict[str, str]:
    """Return the header dict required by the NextLabs PDP REST endpoint.

    The PDP rejects requests without ``Service`` and ``Version`` headers
    with an Indeterminate response (see ``docs/nextlabs_official/pdp_api.md``).

    Args:
        content_type: Wire format for the request body.
        service: Value for the ``Service`` header. Defaults to ``"EVAL"``,
            the only value documented by NextLabs; overridable for custom
            deployments.
        version: Value for the ``Version`` header. Defaults to ``"1.0"``.

    Returns:
        Mapping of header name to value, ready to pass to ``httpx``.
    """
    return {
        CONTENT_TYPE_HEADER: content_type.value,
        SERVICE_HEADER: service,
        VERSION_HEADER: version,
    }
