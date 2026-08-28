# encrypts and hashes personal fields shared across every service
import hashlib
from typing import Final

from cryptography.fernet import Fernet, MultiFernet

_HASH_PREFIX: Final = b"qrew-pii-v1:"


# builds a fernet instance that can decrypt with a rotated key
def make_fernet(primary_key: str, previous_keys: str = "") -> MultiFernet:
    keys = [Fernet(primary_key.encode())]
    for raw in previous_keys.splitlines():
        previous = raw.strip()
        if previous:
            keys.append(Fernet(previous.encode()))
    return MultiFernet(keys)


# encrypts a plaintext field for storage
def encrypt(fernet: MultiFernet, plaintext: str) -> bytes:
    return fernet.encrypt(plaintext.encode())


# decrypts a stored field back to plaintext
def decrypt(fernet: MultiFernet, ciphertext: bytes) -> str:
    return fernet.decrypt(ciphertext).decode()


# encrypts raw bytes for storage
def encrypt_bytes(fernet: MultiFernet, plaintext: bytes) -> bytes:
    return fernet.encrypt(plaintext)


# decrypts stored bytes back to plaintext
def decrypt_bytes(fernet: MultiFernet, ciphertext: bytes) -> bytes:
    return fernet.decrypt(ciphertext)


# hashes a value so it can be looked up without storing it in the clear
def hash_lookup(plaintext: str) -> str:
    normalised = plaintext.strip().lower().encode()
    return hashlib.sha256(_HASH_PREFIX + normalised).hexdigest()
