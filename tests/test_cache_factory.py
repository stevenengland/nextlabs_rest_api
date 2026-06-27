from mockito import mock, when

from nextlabs_sdk._auth._token_cache import _cache_factory as cache_factory
from nextlabs_sdk._auth._token_cache._encrypted_file_token_cache import (
    EncryptedFileTokenCache,
)
from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache


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
