from __future__ import annotations

from click.exceptions import Exit as ClickExit
import pytest

from nextlabs_sdk._cli._parsing import parse_json_payload, parse_key_value_attrs


def test_parse_json_payload_valid() -> None:
    result = parse_json_payload('{"key": "value"}')
    assert result == {"key": "value"}


def test_parse_json_payload_invalid_json() -> None:
    with pytest.raises(ClickExit):
        parse_json_payload("not-json")


def test_parse_json_payload_array_rejected() -> None:
    with pytest.raises(ClickExit):
        parse_json_payload("[1, 2]")


def test_parse_key_value_attrs_valid() -> None:
    result = parse_key_value_attrs(["k1=v1", "k2=v2"])
    assert result == {"k1": "v1", "k2": "v2"}


def test_parse_key_value_attrs_empty() -> None:
    result = parse_key_value_attrs([])
    assert result == {}


def test_parse_key_value_attrs_invalid() -> None:
    with pytest.raises(ClickExit):
        parse_key_value_attrs(["no-equals"])


def test_parse_key_value_attrs_value_with_equals() -> None:
    result = parse_key_value_attrs(["k1=v=2"])
    assert result == {"k1": "v=2"}
