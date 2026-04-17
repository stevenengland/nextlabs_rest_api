from __future__ import annotations

from click.exceptions import Exit as ClickExit
import pytest

from nextlabs_sdk._cli._parsing import parse_json_payload, parse_key_value_attrs


@pytest.mark.parametrize(
    "raw,expected",
    [
        pytest.param('{"key": "value"}', {"key": "value"}, id="object"),
    ],
)
def test_parse_json_payload_valid(raw, expected):
    assert parse_json_payload(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("not-json", id="invalid-json"),
        pytest.param("[1, 2]", id="array-rejected"),
    ],
)
def test_parse_json_payload_rejects(raw):
    with pytest.raises(ClickExit):
        parse_json_payload(raw)


@pytest.mark.parametrize(
    "items,expected",
    [
        pytest.param(["k1=v1", "k2=v2"], {"k1": "v1", "k2": "v2"}, id="two-pairs"),
        pytest.param([], {}, id="empty"),
        pytest.param(["k1=v=2"], {"k1": "v=2"}, id="value-contains-equals"),
    ],
)
def test_parse_key_value_attrs_valid(items, expected):
    assert parse_key_value_attrs(items) == expected


def test_parse_key_value_attrs_invalid():
    with pytest.raises(ClickExit):
        parse_key_value_attrs(["no-equals"])
