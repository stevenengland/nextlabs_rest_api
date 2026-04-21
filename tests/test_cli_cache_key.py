from __future__ import annotations

from dataclasses import dataclass

from nextlabs_sdk._cli._cache_key import cache_key_for, parse_cache_key


@dataclass(frozen=True)
class _Account:
    base_url: str
    username: str
    client_id: str
    kind: str = "cloudaz"


def test_cache_key_cloudaz_appends_kind_and_oidc_path():
    key = cache_key_for(
        _Account(base_url="https://x.example", username="alice", client_id="cc"),
    )
    assert key == "https://x.example/cas/oidc/accessToken|alice|cc|cloudaz"


def test_cache_key_pdp_has_no_path_suffix_and_empty_username():
    key = cache_key_for(
        _Account(
            base_url="https://pdp.example", username="", client_id="cc", kind="pdp"
        ),
    )
    assert key == "https://pdp.example||cc|pdp"


def test_parse_four_segment_cloudaz_key():
    parsed = parse_cache_key(
        "https://x.example/cas/oidc/accessToken|alice|cc|cloudaz",
    )
    assert parsed == ("https://x.example", "alice", "cc", "cloudaz")


def test_parse_four_segment_pdp_key():
    parsed = parse_cache_key("https://pdp.example||cc|pdp")
    assert parsed == ("https://pdp.example", "", "cc", "pdp")


def test_parse_legacy_three_segment_key_defaults_to_cloudaz():
    parsed = parse_cache_key(
        "https://x.example/cas/oidc/accessToken|alice|cc",
    )
    assert parsed == ("https://x.example", "alice", "cc", "cloudaz")


def test_parse_returns_none_for_unknown_kind():
    assert parse_cache_key("https://x||cc|mystery") is None


def test_parse_returns_none_for_cloudaz_missing_path_suffix():
    assert parse_cache_key("https://x|u|cc|cloudaz") is None


def test_parse_returns_none_for_wrong_segment_count():
    assert parse_cache_key("a|b") is None
