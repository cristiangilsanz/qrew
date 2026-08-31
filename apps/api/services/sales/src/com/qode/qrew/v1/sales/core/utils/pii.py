# encrypts personal fields at rest
import security.pii as _pii
from cryptography.fernet import MultiFernet

from com.qode.qrew.v1.sales.core.config import settings


# builds the fernet instance from the configured encryption keys
def _fernet() -> MultiFernet:
    return _pii.make_fernet(settings.pii_encryption_key, settings.pii_encryption_previous_keys)


# encrypts a plaintext field for storage
def encrypt(plaintext: str) -> bytes:
    return _pii.encrypt(_fernet(), plaintext)


# decrypts a stored field back to plaintext
def decrypt(ciphertext: bytes) -> str:
    return _pii.decrypt(_fernet(), ciphertext)
