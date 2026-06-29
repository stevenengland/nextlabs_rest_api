import base64

import keyring

from mockito import mock, spy2, verify, when

from nextlabs_sdk._auth._token_cache import _cache_factory as cache_factory
from nextlabs_sdk._auth._token_cache import _keyring_passphrase_source as kps
from nextlabs_sdk._auth._token_cache import _secret_box as sb
from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._encrypted_file_token_cache import (
    EncryptedFileTokenCache,
)
from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache


def _tok(access_token: str = "id", expires_at: float = 1000.0) -> CachedToken:
    return CachedToken(
        access_token=access_token,
        refresh_token="rt",
        expires_at=expires_at,
        token_type="bearer",
        scope=None,
    )


class TestBuildTokenCache:
    def test_source_present_returns_encrypted(self, tmp_path):
        cache = cache_factory.build_token_cache(
            path=tmp_path / "t.json",
            env={"NEXTLABS_MASTER_PASSWORD": "pw"},
        )
        assert isinstance(cache, EncryptedFileTokenCache)

    def test_no_source_non_tty_plaintext_warns_once(
        self, tmp_path, capsys, monkeypatch
    ):
        monkeypatch.setattr(cache_factory, "_WARNED", False)
        console = mock()
        when(console).isatty().thenReturn(False)
        cache = cache_factory.build_token_cache(
            path=tmp_path / "t.json", env={}, console=console
        )
        cache2 = cache_factory.build_token_cache(
            path=tmp_path / "t.json", env={}, console=console
        )
        assert isinstance(cache, FileTokenCache)
        assert isinstance(cache2, FileTokenCache)
        assert capsys.readouterr().err.count("UNENCRYPTED") == 1

    def test_disable_env_silences_warning(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(cache_factory, "_WARNED", False)
        console = mock()
        when(console).isatty().thenReturn(False)
        cache_factory.build_token_cache(
            path=tmp_path / "t.json",
            env={"NEXTLABS_DISABLE_TOKEN_ENCRYPTION": "1"},
            console=console,
        )
        assert capsys.readouterr().err == ""

    def test_keyring_path_roundtrips_without_argon2(self, tmp_path):
        # given no env secret and an available keyring holding a stored key
        when(keyring).set_password(
            kps._SERVICE, kps._PROBE_ACCOUNT, kps._PROBE_VALUE
        ).thenReturn(None)
        when(keyring).get_password(kps._SERVICE, kps._PROBE_ACCOUNT).thenReturn(
            kps._PROBE_VALUE
        )
        when(keyring).delete_password(kps._SERVICE, kps._PROBE_ACCOUNT).thenReturn(None)
        stored = b"\x33" * kps._KEK_LEN
        when(keyring).get_password(kps._SERVICE, kps._KEK_ACCOUNT).thenReturn(
            base64.b64encode(stored).decode("ascii")
        )
        spy2(sb._derive_kek)
        # when a cache is built and a token is saved then loaded back
        cache = cache_factory.build_token_cache(path=tmp_path / "t.json", env={})
        cache.save("a", _tok())
        loaded = cache.load("a")
        # then the cache is encrypted, round-trips, and no Argon2 derivation runs
        assert isinstance(cache, EncryptedFileTokenCache)
        assert loaded == _tok()
        verify(sb, times=0)._derive_kek(...)


class TestInspectTokenCache:
    def test_inspect_reports_without_unlocking(self, tmp_path):
        path = tmp_path / "tokens.json"
        cache_factory.build_token_cache(
            path=path, env={"NEXTLABS_MASTER_PASSWORD": "pw"}
        ).save("a", _tok())
        spy2(sb._derive_kek)
        status = cache_factory.inspect_token_cache(
            path=path, env={"NEXTLABS_MASTER_PASSWORD": "pw"}
        )
        assert status.state == "encrypted"
        assert status.source == "env"
        assert status.suite_id == 1
        verify(sb, times=0)._derive_kek(...)

    def test_inspect_reports_absent(self, tmp_path):
        status = cache_factory.inspect_token_cache(
            path=tmp_path / "tokens.json", env={}
        )
        assert status.state == "absent"
        assert status.source == "none"
        assert status.suite_id is None

    def test_inspect_reports_plaintext(self, tmp_path):
        path = tmp_path / "tokens.json"
        cache_factory.build_token_cache(path=path, env={}).save("a", _tok())
        status = cache_factory.inspect_token_cache(path=path, env={})
        assert status.state == "plaintext"
        assert status.suite_id is None

    def test_inspect_reports_keyring_label_without_generating_key(self, tmp_path):
        # given an available keyring but no stored key yet
        when(keyring).set_password(
            kps._SERVICE, kps._PROBE_ACCOUNT, kps._PROBE_VALUE
        ).thenReturn(None)
        when(keyring).get_password(kps._SERVICE, kps._PROBE_ACCOUNT).thenReturn(
            kps._PROBE_VALUE
        )
        when(keyring).delete_password(kps._SERVICE, kps._PROBE_ACCOUNT).thenReturn(None)
        # when the absent cache is inspected
        status = cache_factory.inspect_token_cache(
            path=tmp_path / "tokens.json", env={}
        )
        # then the keyring label is reported without persisting a fresh key
        assert status.state == "absent"
        assert status.source == "keyring"
        verify(keyring, times=0).set_password(kps._SERVICE, kps._KEK_ACCOUNT, ...)
