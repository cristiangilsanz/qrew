import security.pii as _pii
from cryptography.fernet import MultiFernet

from com.qode.qrew.v1.identity.core.config import settings


def _fernet() -> MultiFernet:
    return _pii.make_fernet(settings.pii_encryption_key, settings.pii_encryption_previous_keys)


def encrypt(plaintext: str) -> bytes:
    return _pii.encrypt(_fernet(), plaintext)


def decrypt(ciphertext: bytes) -> str:
    return _pii.decrypt(_fernet(), ciphertext)


def encrypt_bytes(plaintext: bytes) -> bytes:
    return _pii.encrypt_bytes(_fernet(), plaintext)


def decrypt_bytes(ciphertext: bytes) -> bytes:
    return _pii.decrypt_bytes(_fernet(), ciphertext)


def hash_lookup(plaintext: str) -> str:
    return _pii.hash_lookup(plaintext)
