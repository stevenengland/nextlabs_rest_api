from __future__ import annotations

from typing import Mapping, Sequence

from nextlabs_sdk._auth._token_cache._env_passphrase_source import (
    EnvVarPassphraseSource,
)
from nextlabs_sdk._auth._token_cache._secret_box import PassphraseKek


class PassphraseResolver:
    """Resolves the first available passphrase source in fixed order.

    This slice wires only the environment source; keyring and TTY sources
    are inserted ahead of the plaintext fallback by later slices.
    """

    def __init__(
        self,
        sources: Sequence[EnvVarPassphraseSource] = (EnvVarPassphraseSource(),),
    ) -> None:
        self._sources = sources

    def resolve(self, env: Mapping[str, str]) -> tuple[PassphraseKek | None, str]:
        for source in self._sources:
            material = source.resolve(env)
            if material is not None:
                return material, source.source_label
        return None, "none"
