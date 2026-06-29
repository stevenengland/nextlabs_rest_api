from __future__ import annotations

import base64
import contextlib
import os
from typing import Mapping

import keyring
from keyring.errors import KeyringError, KeyringLocked, NoKeyringError

from nextlabs_sdk._auth._token_cache._secret_box import RawKek

_SERVICE = "nextlabs-sdk"
_KEK_ACCOUNT = "token-cache-kek"
_PROBE_ACCOUNT = "__probe__"
_PROBE_VALUE = "nextlabs-sdk-probe"
_KEK_LEN = 32


class KeyringPassphraseSource:
    """Passphrase source backed by the OS keyring, wrapping the DEK with a raw KEK.

    On first use a random 32-byte key-encryption key is generated and stored in
    the keyring; later invocations fetch it and wrap the data-encryption key
    directly, with no key-derivation step. A null backend that accepts writes
    but returns ``None`` on read is treated as unavailable so the resolver falls
    through to the next source.
    """

    source_label = "keyring"

    def resolve(self, env: Mapping[str, str]) -> RawKek | None:
        if not self.available():
            return None
        try:
            return self._load_or_create()
        except (NoKeyringError, KeyringLocked):
            return None

    def available(self) -> bool:
        try:
            keyring.set_password(_SERVICE, _PROBE_ACCOUNT, _PROBE_VALUE)
        except (NoKeyringError, KeyringLocked):
            return False
        try:
            roundtrip = keyring.get_password(_SERVICE, _PROBE_ACCOUNT)
        except (NoKeyringError, KeyringLocked):
            roundtrip = None
        finally:
            self._delete_probe()
        return roundtrip == _PROBE_VALUE

    def would_resolve(self, env: Mapping[str, str]) -> bool:
        return self.available()

    def _load_or_create(self) -> RawKek:
        stored = keyring.get_password(_SERVICE, _KEK_ACCOUNT)
        if stored is None:
            return self._generate_and_store()
        return RawKek(key=base64.b64decode(stored))

    def _generate_and_store(self) -> RawKek:
        key = os.urandom(_KEK_LEN)
        keyring.set_password(
            _SERVICE, _KEK_ACCOUNT, base64.b64encode(key).decode("ascii")
        )
        return RawKek(key=key)

    def _delete_probe(self) -> None:
        with contextlib.suppress(KeyringError):
            keyring.delete_password(_SERVICE, _PROBE_ACCOUNT)
