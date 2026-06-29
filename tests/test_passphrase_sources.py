import base64

import keyring
from keyring.errors import KeyringLocked, NoKeyringError
from mockito import ANY, captor, verify, when

from nextlabs_sdk._auth._token_cache import _keyring_passphrase_source as kps
from nextlabs_sdk._auth._token_cache._env_passphrase_source import (
    EnvVarPassphraseSource,
)
from nextlabs_sdk._auth._token_cache._keyring_passphrase_source import (
    KeyringPassphraseSource,
)
from nextlabs_sdk._auth._token_cache._passphrase_resolver import PassphraseResolver
from nextlabs_sdk._auth._token_cache._secret_box import PassphraseKek, RawKek


def _stub_probe_success() -> None:
    when(keyring).set_password(
        kps._SERVICE, kps._PROBE_ACCOUNT, kps._PROBE_VALUE
    ).thenReturn(None)
    when(keyring).get_password(kps._SERVICE, kps._PROBE_ACCOUNT).thenReturn(
        kps._PROBE_VALUE
    )
    when(keyring).delete_password(kps._SERVICE, kps._PROBE_ACCOUNT).thenReturn(None)


class TestKeyringPassphraseSource:
    def test_available_self_test_passes_and_cleans_up_sentinel(self):
        # given a backend whose probe write round-trips back the sentinel
        _stub_probe_success()
        # when availability is checked
        result = KeyringPassphraseSource().available()
        # then the source is available and the sentinel is deleted afterwards
        assert result is True
        verify(keyring).delete_password(kps._SERVICE, kps._PROBE_ACCOUNT)

    def test_available_reports_null_backend_as_unavailable_and_cleans_up(self):
        # given a null backend that accepts writes but returns None on read
        when(keyring).set_password(
            kps._SERVICE, kps._PROBE_ACCOUNT, kps._PROBE_VALUE
        ).thenReturn(None)
        when(keyring).get_password(kps._SERVICE, kps._PROBE_ACCOUNT).thenReturn(None)
        when(keyring).delete_password(kps._SERVICE, kps._PROBE_ACCOUNT).thenReturn(None)
        # when availability is checked
        result = KeyringPassphraseSource().available()
        # then the source is unavailable and the sentinel is still removed
        assert result is False
        verify(keyring).delete_password(kps._SERVICE, kps._PROBE_ACCOUNT)

    def test_available_treats_no_keyring_error_as_unavailable(self):
        # given a backend that raises NoKeyringError on write
        when(keyring).set_password(
            kps._SERVICE, kps._PROBE_ACCOUNT, kps._PROBE_VALUE
        ).thenRaise(NoKeyringError())
        # when availability is checked
        # then no exception surfaces and the source is unavailable
        assert KeyringPassphraseSource().available() is False

    def test_resolve_swallows_keyring_locked_and_returns_none(self):
        # given a locked backend that raises on the probe write
        when(keyring).set_password(
            kps._SERVICE, kps._PROBE_ACCOUNT, kps._PROBE_VALUE
        ).thenRaise(KeyringLocked())
        # when the source is resolved
        # then it yields no material and the keyring error never escapes
        assert KeyringPassphraseSource().resolve({}) is None

    def test_resolve_generates_stores_then_reuses_key(self):
        # given an available backend that holds no key yet
        _stub_probe_success()
        when(keyring).set_password(kps._SERVICE, kps._KEK_ACCOUNT, ANY).thenReturn(None)
        when(keyring).get_password(kps._SERVICE, kps._KEK_ACCOUNT).thenReturn(None)
        source = KeyringPassphraseSource()
        # when the source is resolved the first time
        first = source.resolve({})
        stored = captor()
        verify(keyring).set_password(kps._SERVICE, kps._KEK_ACCOUNT, stored)
        # and the backend now returns the freshly stored key on the next read
        when(keyring).get_password(kps._SERVICE, kps._KEK_ACCOUNT).thenReturn(
            stored.value
        )
        second = source.resolve({})
        # then a 32-byte key was generated, persisted once, and reused verbatim
        expected = RawKek(key=base64.b64decode(stored.value))
        assert len(expected.key) == kps._KEK_LEN
        assert first == expected
        assert second == expected
        verify(keyring, times=1).set_password(kps._SERVICE, kps._KEK_ACCOUNT, ANY)


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

    def test_resolver_returns_keyring_label_for_keyring_source(self):
        # given no env secret and an available keyring holding a stored key
        _stub_probe_success()
        stored = b"\x22" * kps._KEK_LEN
        when(keyring).get_password(kps._SERVICE, kps._KEK_ACCOUNT).thenReturn(
            base64.b64encode(stored).decode("ascii")
        )
        resolver = PassphraseResolver(
            sources=(EnvVarPassphraseSource(), KeyringPassphraseSource())
        )
        # when the resolver runs with an empty environment
        material, label = resolver.resolve({})
        # then the keyring source supplies the material under the keyring label
        assert material == RawKek(key=stored)
        assert label == "keyring"
