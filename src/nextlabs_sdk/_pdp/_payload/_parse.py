"""Decode payload text to a dict using JSON or YAML."""

from __future__ import annotations

import json

from nextlabs_sdk._pdp._payload._format import PayloadFormat
from nextlabs_sdk.exceptions import PdpPayloadError

_YAML_EXTRA_HINT = (
    "YAML support requires PyYAML. Install it with: " "pip install 'nextlabs-sdk[yaml]'"
)


def parse_text(text: str, text_format: PayloadFormat) -> dict[str, object]:
    """Parse ``text`` as JSON or YAML, returning a mapping.

    Raises :class:`PdpPayloadError` on decode errors, non-object roots, or
    when PyYAML is not installed while a YAML path is requested.
    """
    if text_format is PayloadFormat.JSON:
        return _decode_json(text)
    if text_format is PayloadFormat.YAML:
        return _decode_yaml(text)
    raise PdpPayloadError(
        f"Unsupported text format for parsing: {text_format.value}",
    )


def _decode_json(text: str) -> dict[str, object]:
    try:
        decoded = json.loads(text) if text.strip() else None
    except json.JSONDecodeError as exc:
        raise PdpPayloadError(f"Invalid JSON: {exc.msg} at line {exc.lineno}") from None
    return _require_mapping(decoded, source="JSON")


def _decode_yaml(text: str) -> dict[str, object]:
    try:
        import yaml
    except ImportError:
        raise PdpPayloadError(_YAML_EXTRA_HINT) from None
    try:
        decoded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PdpPayloadError(f"Invalid YAML: {exc}") from None
    return _require_mapping(decoded, source="YAML")


def _require_mapping(decoded: object, *, source: str) -> dict[str, object]:
    if decoded is None:
        raise PdpPayloadError(f"Empty {source} payload: expected an object")
    if not isinstance(decoded, dict):
        raise PdpPayloadError(
            f"{source} payload root must be an object, got {type(decoded).__name__}",
        )
    return decoded
