"""Encryption and lookup hashing for stored PII."""

import hashlib
from typing import Final

from cryptography.fernet import Fernet, MultiFernet

from com.qode.qrew.v1.service.settings import settings

_HASH_PREFIX: Final = b"qrew-pii-v1:"


def _multifernet() -> MultiFernet:
    keys = [Fernet(settings.pii_encryption_key.encode())]
    for raw in settings.pii_encryption_previous_keys.splitlines():
        previous = raw.strip()
        if previous:
            keys.append(Fernet(previous.encode()))
    return MultiFernet(keys)


def encrypt(plaintext: str) -> bytes:
    """Encrypt a PII string."""
    return _multifernet().encrypt(plaintext.encode())


def decrypt(ciphertext: bytes) -> str:
    """Decrypt a PII ciphertext."""
    return _multifernet().decrypt(ciphertext).decode()


def hash_lookup(plaintext: str) -> str:
    """Return a deterministic lookup hash for a PII string."""
    normalised = plaintext.strip().lower().encode()
    return hashlib.sha256(_HASH_PREFIX + normalised).hexdigest()
