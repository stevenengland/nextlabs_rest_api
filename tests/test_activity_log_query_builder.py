from __future__ import annotations

import json
from pathlib import Path

import pytest

from nextlabs_sdk._cli._activity_log_query_builder import (
    build_activity_log_query,
)
from nextlabs_sdk.exceptions import NextLabsError


def _write(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload))
    return path


def test_inline_only_uses_flag_values_and_defaults() -> None:
    query = build_activity_log_query(
        None,
        field_name="user_name",
        field_value="alice",
    )

    assert query.field_name == "user_name"
    assert query.field_value == "alice"
    assert query.policy_decision == "AD"
    assert query.sort_by == "ROW_ID"
    assert query.sort_order == "descending"


def test_inline_no_flags_uses_empty_field_defaults() -> None:
    query = build_activity_log_query(None)

    assert query.field_name == ""
    assert query.field_value == ""
    assert query.policy_decision == "AD"
    assert query.sort_by == "ROW_ID"
    assert query.sort_order == "descending"


def test_inline_only_field_name_defaults_field_value_to_empty() -> None:
    query = build_activity_log_query(None, field_name="sapsid")

    assert query.field_name == "sapsid"
    assert query.field_value == ""


def test_inline_only_field_value_defaults_field_name_to_empty() -> None:
    query = build_activity_log_query(None, field_value="R3M")

    assert query.field_name == ""
    assert query.field_value == "R3M"


def test_file_only_preserves_existing_behaviour(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "q.json",
        {
            "policy_decision": "ALLOW",
            "sort_by": "TIME",
            "sort_order": "ascending",
            "field_name": "user_name",
            "field_value": "bob",
            "from_date": 1_700_000_000,
        },
    )

    query = build_activity_log_query(path)

    assert query.policy_decision == "ALLOW"
    assert query.sort_order == "ascending"
    assert query.field_value == "bob"
    assert query.from_date == 1_700_000_000


def test_flag_overrides_file_value(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "q.json",
        {
            "policy_decision": "ALLOW",
            "sort_by": "TIME",
            "sort_order": "ascending",
            "field_name": "user_name",
            "field_value": "bob",
        },
    )

    query = build_activity_log_query(path, field_value="carol")

    assert query.field_value == "carol"
    assert query.policy_decision == "ALLOW"
    assert query.sort_order == "ascending"


def test_flag_not_supplied_keeps_file_value(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "q.json",
        {
            "policy_decision": "ALLOW",
            "sort_by": "TIME",
            "sort_order": "ascending",
            "field_name": "user_name",
            "field_value": "bob",
        },
    )

    query = build_activity_log_query(path)

    assert query.policy_decision == "ALLOW"
    assert query.sort_by == "TIME"


def test_header_list_overrides(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "q.json",
        {
            "policy_decision": "AD",
            "sort_by": "time",
            "sort_order": "descending",
            "field_name": "user_name",
            "field_value": "bob",
            "header": ["a", "b"],
        },
    )

    query = build_activity_log_query(path, header=["x", "y", "z"])

    assert query.header == ["x", "y", "z"]


def test_from_date_parsed_epoch_ms() -> None:
    query = build_activity_log_query(
        None,
        field_name="u",
        field_value="v",
        from_date="1737014400000",
    )

    assert query.from_date == 1_737_014_400_000


def test_from_date_parsed_iso() -> None:
    query = build_activity_log_query(
        None,
        field_name="u",
        field_value="v",
        from_date="2024-01-15T00:00:00+00:00",
    )

    assert query.from_date is not None
    assert query.from_date == 1_705_276_800_000


def test_from_date_parsed_relative(monkeypatch: pytest.MonkeyPatch) -> None:
    from nextlabs_sdk._cli import _time_parser

    monkeypatch.setattr(_time_parser, "now_epoch_ms", lambda: 1_000_000)

    query = build_activity_log_query(
        None,
        field_name="u",
        field_value="v",
        from_date="1s",
    )

    assert query.from_date == 1_000_000 - 1_000


def test_invalid_json_errors(tmp_path: Path) -> None:
    import click

    path = tmp_path / "bad.json"
    path.write_text("{not json")

    with pytest.raises(click.exceptions.Exit):
        build_activity_log_query(path)


def test_invalid_date_errors() -> None:
    with pytest.raises(NextLabsError) as exc_info:
        build_activity_log_query(
            None,
            field_name="u",
            field_value="v",
            from_date="not-a-date",
        )

    assert "from-date" in str(exc_info.value) or "from_date" in str(exc_info.value)


def test_inline_missing_flags_no_longer_errors() -> None:
    query = build_activity_log_query(None)

    assert query.field_name == ""
    assert query.field_value == ""


def test_inline_partial_flags_no_longer_errors() -> None:
    query = build_activity_log_query(None, field_name="u")

    assert query.field_name == "u"
    assert query.field_value == ""


def test_inline_from_date_defaults_to_date_to_now(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nextlabs_sdk._cli import _activity_log_query_builder as builder_mod

    monkeypatch.setattr(builder_mod, "now_epoch_ms", lambda: 4_242_000)

    query = build_activity_log_query(
        None,
        field_name="u",
        field_value="v",
        from_date="1737014400000",
    )

    assert query.from_date == 1_737_014_400_000
    assert query.to_date == 4_242_000


def test_inline_explicit_to_date_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nextlabs_sdk._cli import _activity_log_query_builder as builder_mod

    monkeypatch.setattr(builder_mod, "now_epoch_ms", lambda: 4_242_000)

    query = build_activity_log_query(
        None,
        field_name="u",
        field_value="v",
        from_date="1737014400000",
        to_date="1737100800000",
    )

    assert query.to_date == 1_737_100_800_000


def test_inline_without_from_date_defaults_both(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nextlabs_sdk._cli import _activity_log_query_builder as builder_mod

    monkeypatch.setattr(builder_mod, "now_epoch_ms", lambda: 4_242_000)

    query = build_activity_log_query(
        None,
        field_name="u",
        field_value="v",
    )

    assert query.to_date == 4_242_000
    assert query.from_date == 4_242_000 - 24 * 60 * 60 * 1000


def test_inline_without_dates_defaults_last_24h(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nextlabs_sdk._cli import _activity_log_query_builder as builder_mod

    now_ms = 1_737_014_400_000
    monkeypatch.setattr(builder_mod, "now_epoch_ms", lambda: now_ms)

    query = build_activity_log_query(
        None,
        field_name="u",
        field_value="v",
    )

    assert query.to_date == now_ms
    assert query.from_date == now_ms - 24 * 60 * 60 * 1000


def test_inline_only_to_date_defaults_from_date_24h_earlier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nextlabs_sdk._cli import _activity_log_query_builder as builder_mod

    monkeypatch.setattr(builder_mod, "now_epoch_ms", lambda: 9_999_000)

    query = build_activity_log_query(
        None,
        field_name="u",
        field_value="v",
        to_date="1737100800000",
    )

    assert query.to_date == 1_737_100_800_000
    assert query.from_date == 1_737_100_800_000 - 24 * 60 * 60 * 1000


def test_inline_query_path_forwarded_verbatim(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "q.json",
        {
            "policy_decision": "AD",
            "sort_by": "time",
            "sort_order": "descending",
            "field_name": "u",
            "field_value": "v",
        },
    )

    query = build_activity_log_query(path)

    assert query.sort_by == "time"
    assert query.field_name == "u"
    assert query.field_value == "v"


def test_inline_default_header_applied_when_not_supplied() -> None:
    query = build_activity_log_query(
        None,
        field_name="u",
        field_value="v",
        default_header=["ROW_ID", "TIME", "USER_NAME"],
    )

    assert query.header == ["ROW_ID", "TIME", "USER_NAME"]


def test_inline_supplied_header_overrides_default() -> None:
    query = build_activity_log_query(
        None,
        field_name="u",
        field_value="v",
        header=["A", "B"],
        default_header=["ROW_ID", "TIME", "USER_NAME"],
    )

    assert query.header == ["A", "B"]


def test_file_mode_does_not_inject_to_date_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from nextlabs_sdk._cli import _activity_log_query_builder as builder_mod

    monkeypatch.setattr(builder_mod, "now_epoch_ms", lambda: 4_242_000)

    path = _write(
        tmp_path / "q.json",
        {
            "policy_decision": "AD",
            "sort_by": "time",
            "sort_order": "descending",
            "field_name": "u",
            "field_value": "v",
            "from_date": 1_700_000_000,
        },
    )

    query = build_activity_log_query(path)

    assert query.to_date is None


def test_file_mode_does_not_inject_default_header(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "q.json",
        {
            "policy_decision": "AD",
            "sort_by": "time",
            "sort_order": "descending",
            "field_name": "u",
            "field_value": "v",
        },
    )

    query = build_activity_log_query(path, default_header=["ROW_ID"])

    assert query.header is None
