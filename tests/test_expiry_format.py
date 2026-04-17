from __future__ import annotations

import pytest

from nextlabs_sdk._cli._expiry_format import format_expiry

_NOW = 1_700_000_000.0
_ABSOLUTE = "2023-11-14T22:13:20Z"


@pytest.mark.parametrize(
    ("delta_seconds", "expected_phrase"),
    [
        (45, "in 45 seconds"),
        (1, "in 1 second"),
        (0, "in 0 seconds"),
        (60, "in 1 minute"),
        (59 * 60, "in 59 minutes"),
        (2 * 60 * 60, "in 2 hours"),
        (25 * 60 * 60, "in 1 day"),
        (3 * 24 * 60 * 60, "in 3 days"),
    ],
)
def test_format_expiry_future(delta_seconds: int, expected_phrase: str) -> None:
    rendered = format_expiry(_NOW + delta_seconds, now=_NOW)

    assert rendered.endswith(f"({expected_phrase})")


@pytest.mark.parametrize(
    ("delta_seconds", "expected_phrase"),
    [
        (30, "expired 30 seconds ago"),
        (60, "expired 1 minute ago"),
        (3 * 60, "expired 3 minutes ago"),
        (2 * 60 * 60, "expired 2 hours ago"),
        (2 * 24 * 60 * 60, "expired 2 days ago"),
    ],
)
def test_format_expiry_past(delta_seconds: int, expected_phrase: str) -> None:
    rendered = format_expiry(_NOW - delta_seconds, now=_NOW)

    assert rendered.endswith(f"({expected_phrase})")


def test_format_expiry_uses_utc_iso_prefix() -> None:
    rendered = format_expiry(_NOW, now=_NOW)

    assert rendered.startswith(_ABSOLUTE)


def test_format_expiry_handles_out_of_range_epoch() -> None:
    rendered = format_expiry(1e12, now=_NOW)

    assert rendered.startswith("epoch=1000000000000.0")
    assert rendered.endswith(")")


def test_format_expiry_defaults_now_to_wall_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "nextlabs_sdk._cli._expiry_format.time.time",
        lambda: _NOW,
    )

    rendered = format_expiry(_NOW + 120)

    assert rendered == "2023-11-14T22:15:20Z (in 2 minutes)"
