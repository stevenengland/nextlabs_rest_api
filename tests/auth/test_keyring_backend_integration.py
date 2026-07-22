"""Integration coverage for the keyring passphrase source against a real store.

The rest of the keyring suite (``test_passphrase_sources.py``) stubs the
``keyring`` module functions with mockito: each call is matched to canned
arguments and returns a hard-coded value, so the library's own round-trip,
missing-key (``None``) and missing-delete semantics — the exact contract every
platform backend (Windows Credential Manager, macOS Keychain, Linux Secret
Service / KWallet) must honour — are never exercised.

These tests wire ``keyring.get_password`` / ``set_password`` /
``delete_password`` (the source's entire dependency surface) to a genuine
in-process store that actually persists, returns ``None`` for absent keys and
raises ``PasswordDeleteError`` on a missing delete, then drive
``KeyringPassphraseSource`` end-to-end. This closes the mock-only assurance gap
(#263 F7) for the portable backend behaviour without depending on a real OS
keychain being present in the (headless) test environment.
"""

from __future__ import annotations

from typing import Iterator

import pytest
from keyring.errors import PasswordDeleteError

from nextlabs_sdk._auth._token_cache import _keyring_passphrase_source as kps
from nextlabs_sdk._auth._token_cache._env_passphrase_source import (
    EnvVarPassphraseSource,
)
from nextlabs_sdk._auth._token_cache._keyring_passphrase_source import (
    KeyringPassphraseSource,
)
from nextlabs_sdk._auth._token_cache._passphrase_resolver import PassphraseResolver
from nextlabs_sdk._auth._token_cache._secret_box import RawKek


class _RealStore:
    """A genuine persistent secret store with platform-faithful semantics.

    Unlike a mockito stub, it holds whatever is written, hands it straight back
    on read, yields ``None`` for keys it has never seen, and raises
    ``PasswordDeleteError`` when asked to remove an absent key — mirroring the
    contract the real keyring backends implement.
    """

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], str] = {}

    def fetch(self, service: str, account: str) -> str | None:
        return self._items.get((service, account))

    def store(self, service: str, account: str, secret: str) -> None:
        self._items[(service, account)] = secret

    def remove(self, service: str, account: str) -> None:
        if self._items.pop((service, account), None) is None:
            raise PasswordDeleteError("not set")


@pytest.fixture()
def real_store(monkeypatch: pytest.MonkeyPatch) -> Iterator[_RealStore]:
    # conftest's autouse fixture stubs these to raise NoKeyringError; rebind
    # them to a real persistent store so the source's actual dependency surface
    # is exercised for real rather than mocked.
    store = _RealStore()
    # Rebinds keyring's entire function surface to a real persistent store
    # (integration fixture), not stubbing individual calls.
    monkeypatch.setattr(  # mockito-allow: real-store rebind
        "keyring.get_password", store.fetch
    )
    monkeypatch.setattr(  # mockito-allow: real-store rebind
        "keyring.set_password", store.store
    )
    monkeypatch.setattr(  # mockito-allow: real-store rebind
        "keyring.delete_password", store.remove
    )
    yield store


def test_available_round_trips_probe_through_real_store(
    real_store: _RealStore,
) -> None:
    # given a genuine store that persists writes
    source = KeyringPassphraseSource()
    # when availability is probed
    result = source.available()
    # then the real write->read->delete round-trip reports available and the
    # sentinel is actually gone from storage afterwards
    assert result is True
    assert real_store.fetch(kps._SERVICE, kps._PROBE_ACCOUNT) is None


def test_resolve_generates_persists_then_reuses_key_via_real_store(
    real_store: _RealStore,
) -> None:
    # given an available store holding no key yet
    source = KeyringPassphraseSource()
    # when the source is resolved twice
    first = source.resolve({})
    second = source.resolve({})
    # then a 32-byte raw KEK was generated, truly persisted, and reused verbatim
    assert isinstance(first, RawKek)
    assert len(first.key) == kps._KEK_LEN
    assert first == second
    assert real_store.fetch(kps._SERVICE, kps._KEK_ACCOUNT) is not None


def test_resolver_selects_keyring_label_against_real_store(
    real_store: _RealStore,
) -> None:
    # given no env secret and a real, functional store
    resolver = PassphraseResolver(
        sources=(EnvVarPassphraseSource(), KeyringPassphraseSource()),
    )
    # when the resolver runs end-to-end with an empty environment
    material, label = resolver.resolve({})
    # then the keyring source supplies a raw KEK under the keyring label,
    # truly persisted in the real store
    assert isinstance(material, RawKek)
    assert label == "keyring"
    assert real_store.fetch(kps._SERVICE, kps._KEK_ACCOUNT) is not None
