from nextlabs_sdk._auth._token_cache._env_passphrase_source import (
    EnvVarPassphraseSource,
)
from nextlabs_sdk._auth._token_cache._passphrase_resolver import PassphraseResolver
from nextlabs_sdk._auth._token_cache._secret_box import PassphraseKek


class TestEnvVarPassphraseSource:
    def test_env_source_present_returns_passphrase(self):
        source = EnvVarPassphraseSource()
        result = source.resolve({"NEXTLABS_MASTER_PASSWORD": "pw"})
        assert result == PassphraseKek(passphrase=b"pw")

    def test_env_source_absent_returns_none(self):
        assert EnvVarPassphraseSource().resolve({}) is None


class TestPassphraseResolver:
    def test_resolver_order_env_then_none(self):
        resolver = PassphraseResolver()
        assert resolver.resolve({"NEXTLABS_MASTER_PASSWORD": "pw"}) == (
            PassphraseKek(passphrase=b"pw"),
            "env",
        )
        assert resolver.resolve({}) == (None, "none")
