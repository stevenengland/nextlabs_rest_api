from __future__ import annotations

from typing import Mapping

from nextlabs_sdk._auth._token_cache._console_io import ConsoleIO
from nextlabs_sdk._auth._token_cache._secret_box import PassphraseKek

_PROMPT = "Token cache passphrase (leave empty to skip encryption): "


class InteractivePassphraseSource:
    """Passphrase source that prompts for a secret on the controlling terminal.

    On a TTY the typed passphrase becomes Argon2id material for the
    key-encryption key. A non-interactive input stream reports unavailable
    without reading, so the resolver falls through to the next source instead of
    blocking on a prompt that can never be answered. An empty entry is also
    treated as unavailable, deferring to the plaintext confirmation gate.
    """

    source_label = "tty"

    def __init__(self, console: ConsoleIO) -> None:
        self._console = console

    def resolve(self, env: Mapping[str, str]) -> PassphraseKek | None:
        if not self._console.isatty():
            return None
        passphrase = self._console.prompt_secret(_PROMPT)
        if not passphrase:
            return None
        return PassphraseKek(passphrase=passphrase.encode("utf-8"))

    def would_resolve(self, env: Mapping[str, str]) -> bool:
        return self._console.isatty()
