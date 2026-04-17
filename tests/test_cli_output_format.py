from __future__ import annotations

import pytest

from nextlabs_sdk._cli._output_format import OutputFormat


def test_output_format_has_four_members() -> None:
    assert {m.value for m in OutputFormat} == {"table", "wide", "detail", "json"}


def test_output_format_is_str_enum() -> None:
    assert OutputFormat.TABLE.value == "table"
    assert isinstance(OutputFormat.JSON.value, str)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("table", OutputFormat.TABLE),
        ("TABLE", OutputFormat.TABLE),
        ("wide", OutputFormat.WIDE),
        ("detail", OutputFormat.DETAIL),
        ("json", OutputFormat.JSON),
    ],
)
def test_output_format_parses_case_insensitively(
    raw: str, expected: OutputFormat
) -> None:
    assert OutputFormat(raw.lower()) is expected
