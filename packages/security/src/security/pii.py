import hashlib
from typing import Final

from cryptography.fernet import Fernet, MultiFernet

_HASH_PREFIX: Final = b"qrew-pii-v1:"


def make_fernet(primary_key: str, previous_keys: str = "") -> MultiFernet:
    """Builds a key-rotation-aware Fernet encryptor from a primary key and optional previous keys."""
    keys = [Fernet(primary_key.encode())]
    for raw in previous_keys.splitlines():
        previous = raw.strip()
        if previous:
            keys.append(Fernet(previous.encode()))
    return MultiFernet(keys)


def encrypt(fernet: MultiFernet, plaintext: str) -> bytes:
    """Encrypts a plaintext string using the provided key pool."""
    return fernet.encrypt(plaintext.encode())


def decrypt(fernet: MultiFernet, ciphertext: bytes) -> str:
    """Decrypts a ciphertext to its original string using the provided key pool."""
    return fernet.decrypt(ciphertext).decode()


def encrypt_bytes(fernet: MultiFernet, plaintext: bytes) -> bytes:
    """Encrypts raw bytes using the provided key pool."""
    return fernet.encrypt(plaintext)


def decrypt_bytes(fernet: MultiFernet, ciphertext: bytes) -> bytes:
    """Decrypts raw bytes using the provided key pool."""
    return fernet.decrypt(ciphertext)


def hash_lookup(plaintext: str) -> str:
    """Returns a deterministic hash for PII equality lookups without storing plaintext."""
    normalised = plaintext.strip().lower().encode()
    return hashlib.sha256(_HASH_PREFIX + normalised).hexdigest()
