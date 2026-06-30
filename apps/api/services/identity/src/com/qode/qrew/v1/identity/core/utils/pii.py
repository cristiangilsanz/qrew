import hashlib
from typing import Final

from cryptography.fernet import Fernet, MultiFernet

from com.qode.qrew.v1.identity.core.config import settings

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


def encrypt_bytes(plaintext: bytes) -> bytes:
    """Encrypt a raw byte payload using the PII key pool."""
    return _multifernet().encrypt(plaintext)


def decrypt_bytes(ciphertext: bytes) -> bytes:
    """Decrypt a raw byte payload using the PII key pool."""
    return _multifernet().decrypt(ciphertext)


def hash_lookup(plaintext: str) -> str:
    """Return a deterministic lookup hash for a PII string."""
    normalised = plaintext.strip().lower().encode()
    return hashlib.sha256(_HASH_PREFIX + normalised).hexdigest()
