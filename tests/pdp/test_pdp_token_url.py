from __future__ import annotations

from nextlabs_sdk._pdp._token_url import resolve_pdp_token_url


class TestResolvePdpTokenUrl:
    def test_explicit_token_url_wins_over_everything(self) -> None:
        result = resolve_pdp_token_url(
            base_url="https://pdp.example.com",
            auth_base_url="https://cloudaz.example.com",
            token_url="https://custom.example.com/oauth",
        )
        assert result == "https://custom.example.com/oauth"

    def test_auth_base_url_produces_cas_token(self) -> None:
        result = resolve_pdp_token_url(
            base_url="https://pdp.example.com",
            auth_base_url="https://cloudaz.example.com",
            token_url=None,
        )
        assert result == "https://cloudaz.example.com/cas/token"

    def test_only_base_url_defaults_to_dpc_oauth(self) -> None:
        result = resolve_pdp_token_url(
            base_url="https://pdp.example.com",
            auth_base_url=None,
            token_url=None,
        )
        assert result == "https://pdp.example.com/dpc/oauth"

    def test_trailing_slash_on_base_url_is_stripped(self) -> None:
        result = resolve_pdp_token_url(
            base_url="https://pdp.example.com/",
            auth_base_url=None,
            token_url=None,
        )
        assert result == "https://pdp.example.com/dpc/oauth"

    def test_trailing_slash_on_auth_base_url_is_stripped(self) -> None:
        result = resolve_pdp_token_url(
            base_url="https://pdp.example.com",
            auth_base_url="https://cloudaz.example.com/",
            token_url=None,
        )
        assert result == "https://cloudaz.example.com/cas/token"

    def test_token_url_is_returned_verbatim_even_with_trailing_slash(self) -> None:
        result = resolve_pdp_token_url(
            base_url="https://pdp.example.com",
            auth_base_url=None,
            token_url="https://custom.example.com/oauth/",
        )
        assert result == "https://custom.example.com/oauth/"

    def test_empty_string_token_url_is_treated_as_unset(self) -> None:
        result = resolve_pdp_token_url(
            base_url="https://pdp.example.com",
            auth_base_url=None,
            token_url="",
        )
        assert result == "https://pdp.example.com/dpc/oauth"

    def test_empty_string_auth_base_url_is_treated_as_unset(self) -> None:
        result = resolve_pdp_token_url(
            base_url="https://pdp.example.com",
            auth_base_url="",
            token_url=None,
        )
        assert result == "https://pdp.example.com/dpc/oauth"
