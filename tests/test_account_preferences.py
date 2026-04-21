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


def test_roundtrip_with_pdp_fields():
    prefs = AccountPreferences(
        verify_ssl=True,
        pdp_url="https://pdp.example.com",
        pdp_auth_source="pdp",
    )
    assert AccountPreferences.from_dict(prefs.to_dict()) == prefs


def test_from_dict_tolerates_missing_pdp_fields():
    restored = AccountPreferences.from_dict(
        {"schema_version": 1, "verify_ssl": True},
    )
    assert restored.pdp_url is None
    assert restored.pdp_auth_source is None


@pytest.mark.parametrize(
    "field",
    [
        pytest.param("pdp_url", id="pdp_url"),
        pytest.param("pdp_auth_source", id="pdp_auth_source"),
    ],
)
def test_from_dict_rejects_non_string_pdp_field(field: str):
    with pytest.raises(TypeError, match=field):
        AccountPreferences.from_dict(
            {"schema_version": 1, "verify_ssl": True, field: 42},
        )
