# encrypts and hashes personal fields at rest
import security.pii as _pii
from cryptography.fernet import MultiFernet

from com.qode.qrew.v1.identity.core.config import settings


# builds the fernet instance from the configured encryption keys
def _fernet() -> MultiFernet:
    return _pii.make_fernet(settings.pii_encryption_key, settings.pii_encryption_previous_keys)


# encrypts a plaintext field for storage
def encrypt(plaintext: str) -> bytes:
    return _pii.encrypt(_fernet(), plaintext)


# decrypts a stored field back to plaintext
def decrypt(ciphertext: bytes) -> str:
    return _pii.decrypt(_fernet(), ciphertext)


# encrypts raw bytes for storage
def encrypt_bytes(plaintext: bytes) -> bytes:
    return _pii.encrypt_bytes(_fernet(), plaintext)


# decrypts stored bytes back to plaintext
def decrypt_bytes(ciphertext: bytes) -> bytes:
    return _pii.decrypt_bytes(_fernet(), ciphertext)


# hashes a value so it can be looked up without storing it in the clear
def hash_lookup(plaintext: str) -> str:
    return _pii.hash_lookup(plaintext)
