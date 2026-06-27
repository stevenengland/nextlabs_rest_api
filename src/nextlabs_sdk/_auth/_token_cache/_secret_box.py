from __future__ import annotations

import os
from dataclasses import dataclass
from types import MappingProxyType

from argon2 import low_level
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from nextlabs_sdk.exceptions import TokenCacheError

_MAGIC = b"NLBX"
_VERSION = 1

_WRAP_ARGON2 = 0
_WRAP_RAW = 1

_MAGIC_LEN = 4
_SALT_LEN = 16
_DEK_LEN = 32
_GCM_TAG_LEN = 16
_WRAPPED_DEK_LEN = _DEK_LEN + _GCM_TAG_LEN
_NONCE_LEN = 12

_SALT_OFFSET = 7
_WRAPPED_DEK_OFFSET = _SALT_OFFSET + _SALT_LEN
_HEADER_PREFIX_LEN = _WRAPPED_DEK_OFFSET + _WRAPPED_DEK_LEN

_ZERO_SALT = b"\x00" * _SALT_LEN
_WRAP_NONCE = b"\x00" * _NONCE_LEN

_ARGON2_TIME_COST = 3
_ARGON2_MEMORY_COST = 65536
_ARGON2_PARALLELISM = 4


@dataclass(frozen=True)
class _Argon2Suite:
    time_cost: int
    memory_cost: int
    parallelism: int
    hash_len: int
    salt_len: int


_SUITES = MappingProxyType(
    {
        1: _Argon2Suite(
            time_cost=_ARGON2_TIME_COST,
            memory_cost=_ARGON2_MEMORY_COST,
            parallelism=_ARGON2_PARALLELISM,
            hash_len=_DEK_LEN,
            salt_len=_SALT_LEN,
        ),
    }
)


@dataclass(frozen=True)
class PassphraseKek:
    passphrase: bytes
    suite_id: int = 1


@dataclass(frozen=True)
class RawKek:
    key: bytes


@dataclass(frozen=True)
class Header:
    version: int
    wrap_type: int
    suite_id: int


def _derive_kek(passphrase: bytes, salt: bytes, suite: _Argon2Suite) -> bytes:
    return low_level.hash_secret_raw(
        passphrase,
        salt,
        time_cost=suite.time_cost,
        memory_cost=suite.memory_cost,
        parallelism=suite.parallelism,
        hash_len=_DEK_LEN,
        type=low_level.Type.ID,
    )


class SecretBox:
    """Seals and opens the fixed-layout ``NLBX`` single-slot envelope.

    Holds an in-process data-encryption key (DEK) so that the key
    derivation runs once per cache file and is reused for every
    :meth:`encrypt`/:meth:`decrypt` call within a single invocation.
    """

    def __init__(self, dek: bytes, header_prefix: bytes) -> None:
        self._dek = dek
        self._header_prefix = header_prefix

    @classmethod
    def seal_new(cls, kek_source: PassphraseKek | RawKek) -> SecretBox:
        dek = os.urandom(_DEK_LEN)
        wrap_type, suite_id, salt, kek = _resolve_kek_for_seal(kek_source)
        header_pre_wrap = _pack_pre_wrap(wrap_type, suite_id, salt)
        wrapped_dek = AESGCM(kek).encrypt(_WRAP_NONCE, dek, header_pre_wrap)
        return cls(dek, header_pre_wrap + wrapped_dek)

    @classmethod
    def unlock(cls, blob: bytes, kek_source: PassphraseKek | RawKek) -> SecretBox:
        header = read_header(blob)
        expected_wrap = _WRAP_RAW if isinstance(kek_source, RawKek) else _WRAP_ARGON2
        if header.wrap_type != expected_wrap:
            raise TokenCacheError()

        header_pre_wrap = blob[:_WRAPPED_DEK_OFFSET]
        salt = blob[_SALT_OFFSET:_WRAPPED_DEK_OFFSET]
        wrapped_dek = blob[_WRAPPED_DEK_OFFSET:_HEADER_PREFIX_LEN]
        kek = _resolve_kek_for_unlock(kek_source, header.suite_id, salt)
        try:
            dek = AESGCM(kek).decrypt(_WRAP_NONCE, wrapped_dek, header_pre_wrap)
        except InvalidTag:
            raise TokenCacheError()
        return cls(dek, blob[:_HEADER_PREFIX_LEN])

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = os.urandom(_NONCE_LEN)
        ciphertext = AESGCM(self._dek).encrypt(nonce, plaintext, self._header_prefix)
        return self._header_prefix + nonce + ciphertext

    def decrypt(self, blob: bytes) -> bytes:
        nonce = blob[_HEADER_PREFIX_LEN : _HEADER_PREFIX_LEN + _NONCE_LEN]
        ciphertext = blob[_HEADER_PREFIX_LEN + _NONCE_LEN :]
        try:
            return AESGCM(self._dek).decrypt(nonce, ciphertext, self._header_prefix)
        except InvalidTag:
            raise TokenCacheError()

    @classmethod
    def is_encrypted(cls, blob: bytes) -> bool:
        return blob[:_MAGIC_LEN] == _MAGIC


def read_header(blob: bytes) -> Header:
    """Parse the envelope header without deriving any key."""
    if len(blob) < _HEADER_PREFIX_LEN or blob[:_MAGIC_LEN] != _MAGIC:
        raise TokenCacheError()
    version = blob[4]
    wrap_type = blob[5]
    suite_id = blob[6]
    if version != _VERSION or wrap_type not in {_WRAP_ARGON2, _WRAP_RAW}:
        raise TokenCacheError()
    return Header(version=version, wrap_type=wrap_type, suite_id=suite_id)


def _pack_pre_wrap(wrap_type: int, suite_id: int, salt: bytes) -> bytes:
    return _MAGIC + bytes((_VERSION, wrap_type, suite_id)) + salt


def _resolve_kek_for_seal(
    kek_source: PassphraseKek | RawKek,
) -> tuple[int, int, bytes, bytes]:
    if isinstance(kek_source, RawKek):
        return _WRAP_RAW, 0, _ZERO_SALT, kek_source.key
    suite = _SUITES[kek_source.suite_id]
    salt = os.urandom(suite.salt_len)
    kek = _derive_kek(kek_source.passphrase, salt, suite)
    return _WRAP_ARGON2, kek_source.suite_id, salt, kek


def _resolve_kek_for_unlock(
    kek_source: PassphraseKek | RawKek,
    suite_id: int,
    salt: bytes,
) -> bytes:
    if isinstance(kek_source, RawKek):
        return kek_source.key
    suite = _SUITES.get(suite_id)
    if suite is None:
        raise TokenCacheError()
    return _derive_kek(kek_source.passphrase, salt, suite)
