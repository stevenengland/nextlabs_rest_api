import base64
import io
from typing import Any

import keyring
import pytest
from keyring.errors import NoKeyringError
from mockito import ANY, mock, spy2, verify, when

from nextlabs_sdk._auth._token_cache import _cache_factory as cache_factory
from nextlabs_sdk._auth._token_cache import _keyring_passphrase_source as kps
from nextlabs_sdk._auth._token_cache import _secret_box as sb
from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._encrypted_file_token_cache import (
    EncryptedFileTokenCache,
)
from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache
from nextlabs_sdk.exceptions import TokenCacheError


def _keyring_unavailable() -> None:
    when(keyring).set_password(
        kps._SERVICE, kps._PROBE_ACCOUNT, kps._PROBE_VALUE
    ).thenRaise(NoKeyringError())


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


class TestInteractiveTokenCache:
    def test_tty_passphrase_unlocks_and_roundtrips_with_tty_label(
        self, tmp_path, monkeypatch
    ):
        # given no env secret, an unavailable keyring, and a TTY passphrase
        monkeypatch.setattr(cache_factory, "_WARNED", False)
        _keyring_unavailable()
        console = mock()
        when(console).isatty().thenReturn(True)
        when(console).prompt_secret(ANY).thenReturn("hunter2")
        path = tmp_path / "t.json"
        # when a cache is built and a token round-trips
        cache = cache_factory.build_token_cache(path=path, env={}, console=console)
        cache.save("a", _tok())
        loaded = cache.load("a")
        # then the entered passphrase encrypts and unlocks the cache
        assert isinstance(cache, EncryptedFileTokenCache)
        assert loaded == _tok()

    def test_no_source_tty_confirm_yes_returns_plaintext_with_guidance(
        self, tmp_path, monkeypatch, capsys
    ):
        # given no source, a TTY, an empty passphrase, and a yes confirmation
        monkeypatch.setattr(cache_factory, "_WARNED", False)
        _keyring_unavailable()
        console = mock()
        when(console).isatty().thenReturn(True)
        when(console).prompt_secret(ANY).thenReturn("")
        when(console).confirm(ANY).thenReturn(True)
        # when the cache is built
        cache = cache_factory.build_token_cache(
            path=tmp_path / "t.json", env={}, console=console
        )
        # then a plaintext cache is returned after warning how to encrypt later
        assert isinstance(cache, FileTokenCache)
        assert "NEXTLABS_MASTER_PASSWORD" in capsys.readouterr().err

    def test_no_source_tty_confirm_no_aborts_without_writing(
        self, tmp_path, monkeypatch
    ):
        # given no source, a TTY, an empty passphrase, and a declined confirmation
        monkeypatch.setattr(cache_factory, "_WARNED", False)
        _keyring_unavailable()
        console = mock()
        when(console).isatty().thenReturn(True)
        when(console).prompt_secret(ANY).thenReturn("")
        when(console).confirm(ANY).thenReturn(False)
        path = tmp_path / "t.json"
        # when the cache is built, then the gate aborts and writes nothing
        with pytest.raises(TokenCacheError):
            cache_factory.build_token_cache(path=path, env={}, console=console)
        assert not path.exists()

    def test_confirmation_is_read_via_console_confirm(self, tmp_path, monkeypatch):
        # given a piped stdin must not bypass the gate
        monkeypatch.setattr(cache_factory, "_WARNED", False)
        _keyring_unavailable()
        console = mock()
        when(console).isatty().thenReturn(True)
        when(console).prompt_secret(ANY).thenReturn("")
        when(console).confirm(ANY).thenReturn(True)
        # when the cache is built
        cache_factory.build_token_cache(
            path=tmp_path / "t.json", env={}, console=console
        )
        # then the decision is read through the controlling terminal, not stdin
        verify(console, times=1).confirm(ANY)

    def test_unusable_tty_degrades_to_plaintext_and_loads_legacy(
        self, tmp_path, monkeypatch, capsys
    ):
        # given no source, an unavailable keyring, an isatty-true terminal whose
        # I/O raises io.UnsupportedOperation, and a legacy plaintext tokens.json
        monkeypatch.setattr(cache_factory, "_WARNED", False)
        _keyring_unavailable()
        console = mock()
        when(console).isatty().thenReturn(True)
        when(console).prompt_secret(ANY).thenRaise(
            io.UnsupportedOperation("File or stream is not seekable.")
        )
        when(console).confirm(ANY).thenRaise(
            io.UnsupportedOperation("File or stream is not seekable.")
        )
        path = tmp_path / "tokens.json"
        FileTokenCache(path=path).save("a", _tok())
        # when a cache is built on the unusable controlling terminal
        cache = cache_factory.build_token_cache(path=path, env={}, console=console)
        # then it degrades to plaintext without aborting and the legacy token loads
        assert isinstance(cache, FileTokenCache)
        assert cache.load("a") == _tok()
        assert "UNENCRYPTED" in capsys.readouterr().err

    def test_unusable_tty_then_non_tty_warns_about_plaintext_only_once(
        self, tmp_path, monkeypatch, capsys
    ):
        # given a process whose first build hits an unusable controlling terminal
        monkeypatch.setattr(cache_factory, "_WARNED", False)
        _keyring_unavailable()
        unusable = mock()
        when(unusable).isatty().thenReturn(True)
        when(unusable).prompt_secret(ANY).thenRaise(
            io.UnsupportedOperation("File or stream is not seekable.")
        )
        when(unusable).confirm(ANY).thenRaise(
            io.UnsupportedOperation("File or stream is not seekable.")
        )
        cache_factory.build_token_cache(
            path=tmp_path / "t.json", env={}, console=unusable
        )
        # and a later build in the same process sees a plain non-interactive console
        plain = mock()
        when(plain).isatty().thenReturn(False)
        # when the second build completes
        cache_factory.build_token_cache(path=tmp_path / "t.json", env={}, console=plain)
        # then the user was warned about unencrypted storage only once
        assert capsys.readouterr().err.count("UNENCRYPTED") == 1


class TestRememberPlaintextChoice:
    def _no_source_tty_console(self) -> Any:
        console = mock()
        when(console).isatty().thenReturn(True)
        when(console).prompt_secret(ANY).thenReturn("")
        when(console).message(ANY).thenReturn(None)
        return console

    def test_confirm_then_accept_remember_persists_and_prints_saved_notice(
        self, tmp_path, monkeypatch
    ):
        # given no source, a TTY, plaintext confirmed, and the remember prompt accepted
        monkeypatch.setattr(cache_factory, "_WARNED", False)
        _keyring_unavailable()
        console = self._no_source_tty_console()
        when(console).confirm(cache_factory._CONFIRM_PROMPT).thenReturn(True)
        when(console).confirm(cache_factory._REMEMBER_PROMPT, default=True).thenReturn(
            True
        )
        ack = mock()
        when(ack).is_acknowledged().thenReturn(False)
        when(ack).remember().thenReturn(None)
        # when the cache is built
        cache = cache_factory.build_token_cache(
            path=tmp_path / "t.json", env={}, console=console, ack_store=ack
        )
        # then the choice is persisted and the saved notice is shown
        assert isinstance(cache, FileTokenCache)
        verify(ack, times=1).remember()
        verify(console, times=1).message(cache_factory._SAVED_NOTICE)

    def test_acknowledged_returns_plaintext_silently(self, tmp_path, monkeypatch):
        # given a prior remembered plaintext choice and no source on a TTY
        monkeypatch.setattr(cache_factory, "_WARNED", False)
        _keyring_unavailable()
        console = self._no_source_tty_console()
        ack = mock()
        when(ack).is_acknowledged().thenReturn(True)
        # when the cache is built
        cache = cache_factory.build_token_cache(
            path=tmp_path / "t.json", env={}, console=console, ack_store=ack
        )
        # then a plaintext cache is returned with no hint and no prompt
        assert isinstance(cache, FileTokenCache)
        verify(console, times=0).message(ANY)
        verify(console, times=0).confirm(...)

    def test_declining_remember_does_not_persist(self, tmp_path, monkeypatch):
        # given no source, a TTY, plaintext confirmed, but the remember prompt declined
        monkeypatch.setattr(cache_factory, "_WARNED", False)
        _keyring_unavailable()
        console = self._no_source_tty_console()
        when(console).confirm(cache_factory._CONFIRM_PROMPT).thenReturn(True)
        when(console).confirm(cache_factory._REMEMBER_PROMPT, default=True).thenReturn(
            False
        )
        ack = mock()
        when(ack).is_acknowledged().thenReturn(False)
        # when the cache is built
        cache = cache_factory.build_token_cache(
            path=tmp_path / "t.json", env={}, console=console, ack_store=ack
        )
        # then nothing is persisted and no saved notice is shown
        assert isinstance(cache, FileTokenCache)
        verify(ack, times=0).remember()
        verify(console, times=0).message(cache_factory._SAVED_NOTICE)

    def test_source_present_ignores_acknowledgement_and_encrypts(
        self, tmp_path, monkeypatch
    ):
        # given a remembered plaintext choice but a resolvable passphrase source
        monkeypatch.setattr(cache_factory, "_WARNED", False)
        ack = mock()
        when(ack).is_acknowledged().thenReturn(True)
        # when the cache is built with an env passphrase present
        cache = cache_factory.build_token_cache(
            path=tmp_path / "t.json",
            env={"NEXTLABS_MASTER_PASSWORD": "pw"},
            ack_store=ack,
        )
        # then the remembered choice is ignored and the cache is encrypted
        assert isinstance(cache, EncryptedFileTokenCache)
        verify(ack, times=0).is_acknowledged()


class TestStateAwareHints:
    def _no_source_tty_console(self) -> Any:
        console = mock()
        when(console).isatty().thenReturn(True)
        when(console).prompt_secret(ANY).thenReturn("")
        when(console).message(ANY).thenReturn(None)
        return console

    def test_fresh_prints_first_time_hint_then_confirms(self, tmp_path, monkeypatch):
        # given no source, a TTY, and no cache on disk yet
        monkeypatch.setattr(cache_factory, "_WARNED", False)
        _keyring_unavailable()
        console = self._no_source_tty_console()
        when(console).confirm(ANY).thenReturn(True)
        path = tmp_path / "tokens.json"
        # when the cache is built
        cache = cache_factory.build_token_cache(path=path, env={}, console=console)
        # then the fresh hint is shown before the unchanged confirm gate
        assert isinstance(cache, FileTokenCache)
        verify(console, times=1).message(cache_factory._HINT_FRESH.format(path=path))
        verify(console, times=1).confirm(ANY)

    def test_legacy_plaintext_prints_hint_then_confirms(self, tmp_path, monkeypatch):
        # given no source, a TTY, and an existing unencrypted cache
        monkeypatch.setattr(cache_factory, "_WARNED", False)
        _keyring_unavailable()
        path = tmp_path / "tokens.json"
        FileTokenCache(path=path).save("a", _tok())
        console = self._no_source_tty_console()
        when(console).confirm(ANY).thenReturn(True)
        # when the cache is built
        cache = cache_factory.build_token_cache(path=path, env={}, console=console)
        # then the legacy-plaintext hint is shown before the unchanged confirm gate
        assert isinstance(cache, FileTokenCache)
        verify(console, times=1).message(
            cache_factory._HINT_LEGACY_PLAINTEXT.format(path=path)
        )
        verify(console, times=1).confirm(ANY)

    def test_lockout_prints_hint_and_aborts_without_touching_file(
        self, tmp_path, monkeypatch
    ):
        # given an encrypted cache that no available source can unlock
        monkeypatch.setattr(cache_factory, "_WARNED", False)
        _keyring_unavailable()
        path = tmp_path / "tokens.json"
        cache_factory.build_token_cache(
            path=path, env={"NEXTLABS_MASTER_PASSWORD": "pw"}
        ).save("a", _tok())
        before = path.read_bytes()
        console = self._no_source_tty_console()
        when(console).confirm(ANY).thenReturn(True)
        # when the cache is built with no resolvable passphrase source
        with pytest.raises(TokenCacheError) as excinfo:
            cache_factory.build_token_cache(path=path, env={}, console=console)
        # then the lockout hint is shown, carried on the exception for callers,
        # the confirm gate is skipped, and the encrypted file is left untouched
        expected_hint = cache_factory._HINT_LOCKOUT.format(path=path)
        assert excinfo.value.message == expected_hint
        verify(console, times=1).message(expected_hint)
        verify(console, times=0).confirm(ANY)
        assert path.read_bytes() == before
