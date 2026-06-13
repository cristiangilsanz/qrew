"""Encryption for PII stored at rest (Stripe client secrets)."""
from typing import Final

from cryptography.fernet import Fernet, MultiFernet

from com.qode.qrew.v1.payments.settings import settings

_HASH_PREFIX: Final = b"qrew-pii-v1:"


def _multifernet() -> MultiFernet:
    keys = [Fernet(settings.pii_encryption_key.encode())]
    for raw in settings.pii_encryption_previous_keys.splitlines():
        previous = raw.strip()
        if previous:
            keys.append(Fernet(previous.encode()))
    return MultiFernet(keys)


def encrypt(plaintext: str) -> bytes:
    return _multifernet().encrypt(plaintext.encode())


def decrypt(ciphertext: bytes) -> str:
    return _multifernet().decrypt(ciphertext).decode()
