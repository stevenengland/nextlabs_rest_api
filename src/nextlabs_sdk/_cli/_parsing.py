from __future__ import annotations

import json as json_mod

import typer

from nextlabs_sdk._cli._output import print_error


def parse_json_payload(raw: str) -> dict[str, object]:
    """Parse and validate a JSON string as a dict."""
    try:
        parsed = json_mod.loads(raw)
    except json_mod.JSONDecodeError:
        print_error("Invalid JSON payload")
        raise typer.Exit(code=1)
    if not isinstance(parsed, dict):
        print_error("JSON payload must be an object")
        raise typer.Exit(code=1)
    return parsed


def parse_key_value_attrs(attrs: list[str]) -> dict[str, str]:
    """Parse a list of 'key=value' strings into a dict."""
    parsed: dict[str, str] = {}
    for attr in attrs:
        if "=" not in attr:
            print_error(f"Invalid attribute format: {attr}. Expected key=value")
            raise typer.Exit(code=1)
        attr_key, _, attr_value = attr.partition("=")
        parsed[attr_key] = attr_value
    return parsed
