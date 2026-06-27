import subprocess
import sys


def test_encrypted_cache_publicly_importable():
    import nextlabs_sdk
    from nextlabs_sdk._auth._token_cache._encrypted_file_token_cache import (
        EncryptedFileTokenCache,
    )

    assert nextlabs_sdk.EncryptedFileTokenCache is EncryptedFileTokenCache
    assert "EncryptedFileTokenCache" in nextlabs_sdk.__all__


def test_import_does_not_pull_keyring():
    code = (
        "import nextlabs_sdk, sys; "
        "assert 'keyring' not in sys.modules, "
        "sorted(m for m in sys.modules if 'keyring' in m)"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
