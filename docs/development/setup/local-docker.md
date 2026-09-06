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

## Networks

The stack is not on a single flat network. `docker-compose.yml` declares three bridge networks, and each container joins only the ones it needs.

| Network | Members |
|---|---|
| `publica` | `frontend`, `gateway` |
| `interna` | `gateway`, the seven domain services, the ten background containers, `nats`, `jaeger` |
| `datos` | The seven domain services, the ten background containers, `postgres`, `redis` |

The gateway therefore reaches the services but not the databases, and the frontend reaches only the gateway. If you add a container, give it the networks it needs, or it will fail to resolve its dependencies by name.

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
| NATS monitoring | `8222` |
| Jaeger UI | `16686` |
| Jaeger OTLP | `4317`, `4318` |

Only the frontend, the gateway and the stateful containers publish their port to the host. The domain services listen on `8001` to `8007` inside the `interna` network, so reach them through the gateway rather than directly.