"""Tests for tests._openapi.examples and placeholders."""

from __future__ import annotations

import json

import pytest

from tests._openapi.examples import ExampleCase, collect_example_cases
from tests._openapi.placeholders import substitute


def test_substitute_replaces_id_with_integer_literal() -> None:
    result = substitute('{"id": {id}, "name": "x"}')
    parsed = json.loads(result)
    assert isinstance(parsed["id"], int)


def test_substitute_is_idempotent_on_clean_strings() -> None:
    clean = '{"x": 1}'
    assert substitute(clean) == clean


def test_substitute_unknown_placeholder_raises() -> None:
    with pytest.raises(ValueError, match="unknown placeholder"):
        substitute('{"x": {never_seen}}')


def test_collect_example_cases_yields_at_least_100_cases() -> None:
    cases = list(collect_example_cases())
    assert len(cases) >= 100
    assert all(isinstance(c, ExampleCase) for c in cases)


def test_example_case_has_expected_shape() -> None:
    cases = list(collect_example_cases())
    case = cases[0]
    assert case.path.startswith("/console/")
    assert case.method in {"get", "post", "put", "delete", "patch"}
    assert case.status in {"200", "201", "400", "500"}
    assert case.content_type in {"application/json", "*/*"}
    assert isinstance(case.body, str)
