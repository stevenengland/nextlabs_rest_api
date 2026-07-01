from __future__ import annotations

from mockito import mock, verify, when

from nextlabs_sdk._cli._account_prefs_plaintext_ack_store import (
    AccountPrefsPlaintextAckStore,
)
from nextlabs_sdk._cli._account_preferences import GlobalCachePreferences
from nextlabs_sdk._cli._account_preferences_store import AccountPreferencesStore


def test_is_acknowledged_true_when_flag_persisted() -> None:
    # given a store holding an acknowledged global cache preference
    store = mock(AccountPreferencesStore)
    when(store).load_global_cache().thenReturn(
        GlobalCachePreferences(plaintext_acknowledged=True)
    )
    adapter = AccountPrefsPlaintextAckStore(store)
    # when the acknowledgement is queried, then it reports true
    assert adapter.is_acknowledged() is True


def test_is_acknowledged_false_when_absent() -> None:
    # given a store with no global cache preference
    store = mock(AccountPreferencesStore)
    when(store).load_global_cache().thenReturn(None)
    adapter = AccountPrefsPlaintextAckStore(store)
    # when the acknowledgement is queried, then it reports false
    assert adapter.is_acknowledged() is False


def test_remember_persists_acknowledged_preference() -> None:
    # given an adapter over a preferences store
    store = mock(AccountPreferencesStore)
    when(store).save_global_cache(...).thenReturn(None)
    adapter = AccountPrefsPlaintextAckStore(store)
    # when the choice is remembered
    adapter.remember()
    # then the acknowledged preference is saved
    verify(store, times=1).save_global_cache(
        GlobalCachePreferences(plaintext_acknowledged=True)
    )
