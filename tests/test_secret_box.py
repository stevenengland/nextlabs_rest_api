import pytest

from nextlabs_sdk._auth._token_cache._secret_box import (
    PassphraseKek,
    RawKek,
    SecretBox,
)
from nextlabs_sdk.exceptions import TokenCacheError


def test_argon2_round_trip():
    kek = PassphraseKek(passphrase=b"hunter2")
    box = SecretBox.seal_new(kek)
    blob = box.encrypt(b'{"k":"v"}')
    assert blob.startswith(b"NLBX")
    reopened = SecretBox.unlock(blob, PassphraseKek(passphrase=b"hunter2"))
    assert reopened.decrypt(blob) == b'{"k":"v"}'


def test_raw_wrap_round_trip():
    key = b"\x11" * 32
    box = SecretBox.seal_new(RawKek(key=key))
    blob = box.encrypt(b"payload")
    assert SecretBox.unlock(blob, RawKek(key=key)).decrypt(blob) == b"payload"


def test_wrong_passphrase_rejects():
    blob = SecretBox.seal_new(PassphraseKek(passphrase=b"right")).encrypt(b"x")
    with pytest.raises(TokenCacheError):
        SecretBox.unlock(blob, PassphraseKek(passphrase=b"wrong"))


def test_tampered_ciphertext_rejects():
    box = SecretBox.seal_new(PassphraseKek(passphrase=b"pw"))
    blob = box.encrypt(b"some-token-data")
    tampered = blob[:-1] + bytes([blob[-1] ^ 1])
    reopened = SecretBox.unlock(blob, PassphraseKek(passphrase=b"pw"))
    with pytest.raises(TokenCacheError):
        reopened.decrypt(tampered)


def test_tampered_header_rejects():
    kek = PassphraseKek(passphrase=b"pw")
    blob = SecretBox.seal_new(kek).encrypt(b"data")

    suite_tampered = blob[:6] + bytes([blob[6] ^ 1]) + blob[7:]
    with pytest.raises(TokenCacheError):
        SecretBox.unlock(suite_tampered, PassphraseKek(passphrase=b"pw"))

    salt_tampered = blob[:7] + bytes([blob[7] ^ 1]) + blob[8:]
    with pytest.raises(TokenCacheError):
        SecretBox.unlock(salt_tampered, PassphraseKek(passphrase=b"pw"))
