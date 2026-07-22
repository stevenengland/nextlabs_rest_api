from __future__ import annotations

import pytest
import typer

from nextlabs_sdk._cli._bulk_ids import parse_bulk_ids


def test_parse_bulk_ids_from_repeated_ids_only() -> None:
    assert parse_bulk_ids([1, 2, 3], None) == [1, 2, 3]


def test_parse_bulk_ids_from_csv_only() -> None:
    assert parse_bulk_ids(None, "4,5,6") == [4, 5, 6]


def test_parse_bulk_ids_merges_sources_preserving_order() -> None:
    assert parse_bulk_ids([1, 2], "3,4") == [1, 2, 3, 4]


def test_parse_bulk_ids_deduplicates_preserving_first_occurrence() -> None:
    assert parse_bulk_ids([1, 2, 1], "2,3,1") == [1, 2, 3]


def test_parse_bulk_ids_accepts_whitespace_in_csv() -> None:
    assert parse_bulk_ids(None, " 1 , 2 , 3 ") == [1, 2, 3]


def test_parse_bulk_ids_ignores_empty_list_arg() -> None:
    assert parse_bulk_ids([], "7") == [7]


def test_parse_bulk_ids_rejects_empty_inputs() -> None:
    with pytest.raises(typer.Exit) as exc:
        parse_bulk_ids(None, None)
    assert exc.value.exit_code == 1


def test_parse_bulk_ids_rejects_empty_csv_string() -> None:
    with pytest.raises(typer.Exit) as exc:
        parse_bulk_ids(None, "")
    assert exc.value.exit_code == 1


def test_parse_bulk_ids_rejects_csv_with_only_separators() -> None:
    with pytest.raises(typer.Exit) as exc:
        parse_bulk_ids(None, " , , ")
    assert exc.value.exit_code == 1


def test_parse_bulk_ids_rejects_non_integer_csv_element(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(typer.Exit):
        parse_bulk_ids(None, "1,abc,3")
    captured = capsys.readouterr()
    assert "abc" in captured.out
