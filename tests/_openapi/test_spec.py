"""Tests for tests._openapi.spec."""

from __future__ import annotations

from tests._openapi.spec import load_spec


def test_load_spec_returns_openapi_3_1() -> None:
    spec = load_spec()
    assert spec["openapi"].startswith("3.")
    assert isinstance(spec["paths"], dict)
    assert len(spec["paths"]) >= 50


def test_load_spec_is_cached() -> None:
    assert load_spec() is load_spec()
