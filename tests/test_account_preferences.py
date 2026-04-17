from __future__ import annotations

import pytest

from nextlabs_sdk._cli._account_preferences import AccountPreferences


def test_to_dict_round_trip_preserves_verify_ssl():
    prefs = AccountPreferences(verify_ssl=False)
    assert AccountPreferences.from_dict(prefs.to_dict()) == prefs


def test_to_dict_round_trip_true():
    prefs = AccountPreferences(verify_ssl=True)
    assert AccountPreferences.from_dict(prefs.to_dict()) == prefs


def test_to_dict_includes_schema_version():
    payload = AccountPreferences(verify_ssl=True).to_dict()
    assert payload["schema_version"] == 1


def test_from_dict_rejects_missing_schema_version():
    with pytest.raises(TypeError, match="schema"):
        AccountPreferences.from_dict({"verify_ssl": True})


def test_from_dict_rejects_unknown_schema_version():
    with pytest.raises(TypeError, match="schema"):
        AccountPreferences.from_dict({"schema_version": 999, "verify_ssl": True})


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("yes", id="string"),
        pytest.param(1, id="int"),
        pytest.param(None, id="none"),
    ],
)
def test_from_dict_rejects_non_bool_verify_ssl(value: object):
    with pytest.raises(TypeError, match="verify_ssl"):
        AccountPreferences.from_dict(
            {"schema_version": 1, "verify_ssl": value},
        )
