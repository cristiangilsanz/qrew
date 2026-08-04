# Local · Native

Runs each service directly on your machine.

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

**2. Bootstrap**

Sets up the virtual environment, installs all dependencies, starts infrastructure, and applies migrations:

```bash
just setup
```

**3. Start backend**

Each service runs in its own terminal:

```bash
just identity-dev    # :8001
just catalog-dev     # :8002
just sales-dev       # :8003
just payments-dev    # :8004
just ticketing-dev   # :8005
just entry-dev       # :8006
just audit-dev       # :8007
just gateway-dev     # :8000
```

**4. Start frontend**

```bash
npm run dev
```

**5. Seed**

```bash
just db-seed
```

## Resuming

After the initial setup, use `just resume` instead of `just setup` to restart infrastructure without wiping the database:

```bash
just resume
```

## Ports

| Service | Port |
|---|---|
| Frontend | `5173` |
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
