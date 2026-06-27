from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Mapping

from nextlabs_sdk._auth._token_cache._console_io import ConsoleIO
from nextlabs_sdk._auth._token_cache._encrypted_file_token_cache import (
    EncryptedFileTokenCache,
)
from nextlabs_sdk._auth._token_cache._file_token_cache import (
    FileTokenCache,
    _default_path,
)
from nextlabs_sdk._auth._token_cache._passphrase_resolver import PassphraseResolver
from nextlabs_sdk._auth._token_cache._token_cache import TokenCache

_DISABLE_ENCRYPTION_ENV = "NEXTLABS_DISABLE_TOKEN_ENCRYPTION"
_PLAINTEXT_WARNING = (
    "warning: token cache is stored UNENCRYPTED; set NEXTLABS_MASTER_PASSWORD "
    "to encrypt it, or NEXTLABS_DISABLE_TOKEN_ENCRYPTION=1 to silence this warning"
)

_WARNED = False


def build_token_cache(
    *,
    path: Path | str | None = None,
    env: Mapping[str, str] = os.environ,
    console: ConsoleIO | None = None,
) -> TokenCache:
    """Build a token cache, encrypting when a passphrase source is present.

    With no source available the cache falls back to plaintext and emits a
    single process-wide warning to stderr; it never aborts. Setting
    ``NEXTLABS_DISABLE_TOKEN_ENCRYPTION=1`` silences the warning.
    """
    console = console or ConsoleIO()
    material, _label = PassphraseResolver().resolve(env)
    cache_path = _default_path() if path is None else Path(path)

    if material is not None:
        return EncryptedFileTokenCache(path=cache_path, kek_source=material)

    _warn_plaintext_once(env)
    return FileTokenCache(path=cache_path)


def _warn_plaintext_once(env: Mapping[str, str]) -> None:
    if env.get(_DISABLE_ENCRYPTION_ENV) == "1" or _WARNED:
        return
    print(_PLAINTEXT_WARNING, file=sys.stderr)
    globals()["_WARNED"] = True
