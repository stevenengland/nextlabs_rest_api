from __future__ import annotations

import pytest

from nextlabs_sdk._cli._time_parser import parse_time

_NOW_MS = 1_700_000_000_000


def test_epoch_ms_returned_unchanged() -> None:
    assert parse_time("1737014400000", now_ms=_NOW_MS) == 1737014400000


def test_zero_epoch_is_preserved() -> None:
    assert parse_time("0", now_ms=_NOW_MS) == 0


@pytest.mark.parametrize(
    ("value", "offset_ms"),
    [
        ("30s", 30 * 1000),
        ("5m", 5 * 60 * 1000),
        ("2h", 2 * 60 * 60 * 1000),
        ("3d", 3 * 24 * 60 * 60 * 1000),
        ("1w", 7 * 24 * 60 * 60 * 1000),
    ],
)
def test_relative_offsets_subtract_from_now(value: str, offset_ms: int) -> None:
    assert parse_time(value, now_ms=_NOW_MS) == _NOW_MS - offset_ms


def test_iso_date_parses_as_midnight_utc() -> None:
    # 2024-01-15T00:00:00Z -> 1705276800000
    assert parse_time("2024-01-15", now_ms=_NOW_MS) == 1705276800000


def test_iso_datetime_naive_is_treated_as_utc() -> None:
    # 2024-01-15T10:30:00Z -> 1705314600000
    assert parse_time("2024-01-15T10:30:00", now_ms=_NOW_MS) == 1705314600000


def test_iso_datetime_with_offset_respects_offset() -> None:
    # 2024-01-15T10:30:00+02:00 == 2024-01-15T08:30:00Z -> 1705307400000
    assert parse_time("2024-01-15T10:30:00+02:00", now_ms=_NOW_MS) == 1705307400000


def test_now_defaults_to_wall_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "nextlabs_sdk._cli._time_parser.time.time",
        lambda: _NOW_MS / 1000,
    )

    assert parse_time("5m") == _NOW_MS - 5 * 60 * 1000


@pytest.mark.parametrize(
    "value",
    [
        "yesterday",
        "5x",
        "",
        "-100",
        "not-a-date",
        "1h2m",
        "1.5h",
    ],
)
def test_invalid_inputs_raise_value_error(value: str) -> None:
    with pytest.raises(ValueError, match="accepted formats"):
        parse_time(value, now_ms=_NOW_MS)
