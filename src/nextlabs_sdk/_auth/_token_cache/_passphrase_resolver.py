from __future__ import annotations

from typing import Mapping, Protocol, Sequence

from nextlabs_sdk._auth._token_cache._env_passphrase_source import (
    EnvVarPassphraseSource,
)
from nextlabs_sdk._auth._token_cache._keyring_passphrase_source import (
    KeyringPassphraseSource,
)
from nextlabs_sdk._auth._token_cache._secret_box import PassphraseKek, RawKek


class PassphraseSource(Protocol):
    """A resolver-pluggable provider of key-encryption-key material."""

    source_label: str

    def resolve(self, env: Mapping[str, str]) -> PassphraseKek | RawKek | None: ...

    def would_resolve(self, env: Mapping[str, str]) -> bool: ...


class PassphraseResolver:
    """Resolves the first available passphrase source in fixed order.

    Sources are consulted in order: the environment variable, then the OS
    keyring. The TTY prompt source is inserted ahead of the plaintext fallback
    by a later slice.
    """

    def __init__(
        self,
        sources: Sequence[PassphraseSource] = (
            EnvVarPassphraseSource(),
            KeyringPassphraseSource(),
        ),
    ) -> None:
        self._sources = sources

    def resolve(
        self, env: Mapping[str, str]
    ) -> tuple[PassphraseKek | RawKek | None, str]:
        for source in self._sources:
            material = source.resolve(env)
            if material is not None:
                return material, source.source_label
        return None, "none"

    def peek(self, env: Mapping[str, str]) -> str:
        """Return the label of the source that would resolve, without using it.

        Unlike :meth:`resolve`, this never materialises key material, so callers
        that only need the selected source's identity (such as cache inspection)
        do not trigger key generation or persistence as a side effect.
        """
        for source in self._sources:
            if source.would_resolve(env):
                return source.source_label
        return "none"
