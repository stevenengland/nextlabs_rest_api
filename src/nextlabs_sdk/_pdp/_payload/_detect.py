"""Detect whether a payload text is JSON or YAML."""

from __future__ import annotations

import json

from nextlabs_sdk._pdp._payload._format import PayloadFormat


def detect_text_format(text: str) -> PayloadFormat:
    """Return :data:`PayloadFormat.JSON` when ``text`` is valid JSON, else YAML.

    Structured-vs-raw-XACML is decided later by shape, not by this helper.
    """
    stripped = text.strip()
    if not stripped:
        return PayloadFormat.JSON
    try:
        json.loads(stripped)
    except ValueError:
        return PayloadFormat.YAML
    return PayloadFormat.JSON
