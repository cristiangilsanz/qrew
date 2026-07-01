import security.pii as _pii
from cryptography.fernet import MultiFernet

from com.qode.qrew.v1.payments.core.config import settings


def _fernet() -> MultiFernet:
    return _pii.make_fernet(settings.pii_encryption_key, settings.pii_encryption_previous_keys)


def encrypt(plaintext: str) -> bytes:
    return _pii.encrypt(_fernet(), plaintext)


def decrypt(ciphertext: bytes) -> str:
    return _pii.decrypt(_fernet(), ciphertext)
