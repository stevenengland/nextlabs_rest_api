from __future__ import annotations

import pytest

from nextlabs_sdk._cli._body_limit import resolve_body_limit


@pytest.mark.parametrize(
    "verbose,env_value,expected",
    [
        pytest.param(0, None, 2000, id="default-vv-level-2"),
        pytest.param(2, None, 2000, id="vv-keeps-2000"),
        pytest.param(3, None, None, id="vvv-unlimited"),
        pytest.param(4, None, None, id="vvvv-also-unlimited"),
        pytest.param(2, "0", None, id="env-zero-means-unlimited"),
        pytest.param(0, "0", None, id="env-zero-wins-at-any-level"),
        pytest.param(2, "500", 500, id="env-positive-overrides"),
        pytest.param(3, "500", 500, id="env-wins-over-verbose"),
        pytest.param(2, "abc", 2000, id="env-invalid-falls-back"),
        pytest.param(2, "-1", 2000, id="env-negative-falls-back"),
        pytest.param(2, "", 2000, id="env-empty-falls-back"),
        pytest.param(3, "not-an-int", None, id="invalid-env-falls-back-to-verbose"),
    ],
)
def test_resolve_body_limit(verbose, env_value, expected):
    assert resolve_body_limit(verbose, env_value) == expected


def test_logging_body_limit_holder_defaults_to_2000():
    from nextlabs_sdk import _logging

    _logging.set_effective_body_limit(2000)
    assert _logging.get_effective_body_limit() == 2000


def test_logging_body_limit_holder_can_be_unlimited():
    from nextlabs_sdk import _logging

    try:
        _logging.set_effective_body_limit(None)
        assert _logging.get_effective_body_limit() is None
    finally:
        _logging.set_effective_body_limit(2000)


def test_logging_body_limit_holder_accepts_custom_int():
    from nextlabs_sdk import _logging

    try:
        _logging.set_effective_body_limit(500)
        assert _logging.get_effective_body_limit() == 500
    finally:
        _logging.set_effective_body_limit(2000)
