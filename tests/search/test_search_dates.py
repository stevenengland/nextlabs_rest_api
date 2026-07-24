from __future__ import annotations

import pytest

from nextlabs_sdk.cloudaz import date_value
from nextlabs_sdk.exceptions import SearchExpressionError


def test_keyword_sets_date_option():
    # given a recognised date keyword
    raw = "PAST_7_DAYS"

    # when the date value is parsed
    payload = date_value(raw)

    # then it carries a Date payload with the keyword as dateOption
    assert payload == {"type": "Date", "dateOption": "PAST_7_DAYS"}


def test_keyword_is_case_insensitive():
    # given a date keyword in lower case
    raw = "past_30_days"

    # when the date value is parsed
    payload = date_value(raw)

    # then the keyword resolves to the upper-case dateOption
    assert payload == {"type": "Date", "dateOption": "PAST_30_DAYS"}


def test_iso_range_parses_to_epoch_milliseconds():
    # given an explicit from..to ISO date range
    raw = "2024-01-01..2024-02-01"

    # when the date value is parsed
    payload = date_value(raw)

    # then both bounds become UTC epoch-millisecond fromDate/toDate
    assert payload == {
        "type": "Date",
        "fromDate": 1704067200000,
        "toDate": 1706745600000,
    }


def test_unknown_keyword_raises_search_expression_error():
    # given a value that is neither a known keyword nor a range
    raw = "BOGUS"

    # when the date value is parsed
    # then a SearchExpressionError is raised
    with pytest.raises(SearchExpressionError):
        date_value(raw)


def test_malformed_range_bound_raises_search_expression_error():
    # given a range with an unparseable ISO bound
    raw = "2024-01-01..not-a-date"

    # when the date value is parsed
    # then a SearchExpressionError is raised
    with pytest.raises(SearchExpressionError):
        date_value(raw)


def test_range_missing_upper_bound_raises_search_expression_error():
    # given a range with an empty upper bound
    raw = "2024-01-01.."

    # when the date value is parsed
    # then a SearchExpressionError is raised
    with pytest.raises(SearchExpressionError):
        date_value(raw)
