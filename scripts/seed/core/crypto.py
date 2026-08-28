# mirrors the encryption and hashing every service applies to personal fields

from __future__ import annotations

import hashlib
from functools import lru_cache

from cryptography.fernet import MultiFernet
from passlib.context import CryptContext

_HASH_PREFIX = b"qrew-pii-v1:"
_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


# encrypts a value the same way the services store it
def encrypt(fernet: MultiFernet, value: str) -> bytes:
    return fernet.encrypt(value.encode())


# hashes a value the same way the services look it up
def hash_pii(value: str) -> str:
    return hashlib.sha256(_HASH_PREFIX + value.strip().lower().encode()).hexdigest()


# hashes a password the same way identity stores it
@lru_cache(maxsize=8)
def hash_password(password: str) -> str:
    return _context.hash(password)
