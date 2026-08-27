"""Encryption and hashing helpers that mirror what the services do at runtime."""

from __future__ import annotations

import hashlib
from functools import lru_cache

from cryptography.fernet import MultiFernet
from passlib.context import CryptContext

_HASH_PREFIX = b"qrew-pii-v1:"
_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def encrypt(fernet: MultiFernet, value: str) -> bytes:
    return fernet.encrypt(value.encode())


def hash_pii(value: str) -> str:
    return hashlib.sha256(_HASH_PREFIX + value.strip().lower().encode()).hexdigest()


@lru_cache(maxsize=8)
def hash_password(password: str) -> str:
    """Argon2 is slow on purpose, so an identical password is only hashed once."""
    return _context.hash(password)
