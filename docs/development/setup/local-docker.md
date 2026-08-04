# Local · Docker

Runs the entire stack in containers.

## Prerequisites

Before continuing, complete:

1. [Prerequisites](../prerequisites.md) — Required tools installed
2. [Configuration](../configuration.md) — Example files copied and secrets filled in

## Setup

**1. Clone**

```bash
git clone https://github.com/cristiangilsanz/qrew.git
cd qrew
```

**2. Start**

```bash
just up
```

**3. Seed**

```bash
just db-seed
```

## Ports

| Service | Port |
|---|---|
| Frontend | `3000` |
| Gateway | `8000` |
| Identity | `8001` |
| Catalog | `8002` |
| Sales | `8003` |
| Payments | `8004` |
| Ticketing | `8005` |
| Entry | `8006` |
| Audit | `8007` |
| PostgreSQL | `5432` |
| Redis | `6379` |
| NATS | `4222` |