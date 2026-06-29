from __future__ import annotations

from typing import Mapping

from nextlabs_sdk._auth._token_cache._secret_box import PassphraseKek

_MASTER_PASSWORD_ENV = "NEXTLABS_MASTER_PASSWORD"


class EnvVarPassphraseSource:
    """Passphrase source backed by the ``NEXTLABS_MASTER_PASSWORD`` env var."""

    source_label = "env"

    def resolve(self, env: Mapping[str, str]) -> PassphraseKek | None:
        secret = env.get(_MASTER_PASSWORD_ENV)
        if not secret:
            return None
        return PassphraseKek(passphrase=secret.encode("utf-8"))

    def would_resolve(self, env: Mapping[str, str]) -> bool:
        return bool(env.get(_MASTER_PASSWORD_ENV))
