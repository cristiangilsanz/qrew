# loads the database dsn and encryption key from identity's local config

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from cryptography.fernet import Fernet, MultiFernet

REPO_ROOT = Path(__file__).resolve().parents[3]
IDENTITY_CONFIG = REPO_ROOT / "apps/api/services/identity/config/local.yaml"


@dataclass(frozen=True)
class SeedConfig:
    dsn: str
    fernet: MultiFernet
    redis_url: str


# converts the async database url into the plain dsn asyncpg expects
def _dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


# builds the fernet instance from the primary and previous encryption keys
def _fernet(key: str, previous: str) -> MultiFernet:
    keys = [Fernet(key.encode())]
    keys.extend(
        Fernet(line.strip().encode()) for line in previous.splitlines() if line.strip()
    )
    return MultiFernet(keys)


# loads the seed configuration from identity's local yaml
def load(path: Path | None = None) -> SeedConfig:
    source = path or IDENTITY_CONFIG
    if not source.exists():
        raise SystemExit(
            f"Missing configuration: {source}. Copy the example file first."
        )
    raw = yaml.safe_load(source.read_text())
    return SeedConfig(
        dsn=_dsn(raw["database_url"]),
        fernet=_fernet(
            raw["pii_encryption_key"], raw.get("pii_encryption_previous_keys", "")
        ),
        redis_url=raw.get("redis_url", "redis://localhost:6379/0"),
    )
