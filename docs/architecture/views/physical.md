# Physical view

> [!NOTE]
> The physical view describes how the software maps onto machines today. It documents the
> environment that exists, not a target deployment.

The system runs as a single Docker Compose stack. Every component is a container on one host,
the domain services are reachable only through the API Gateway, and the data stores are the
sole stateful pieces.

<div align="center">

```mermaid
flowchart TB
    dev(["Developer host"]):::ext

    subgraph Compose["Docker Compose stack"]
        web["Web interface · nginx :3000"]:::edge
        gw["API Gateway :8000"]:::edge

        subgraph Services["Domain services"]
            identity["Identity :8001"]:::svc
            catalog["Catalog :8002"]:::svc
            sales["Sales :8003"]:::svc
            payments["Payments :8004"]:::svc
            ticketing["Ticketing :8005"]:::svc
            entry["Entry :8006"]:::svc
            audit["Audit :8007"]:::svc
        end

        workers["Workers × 7 + job runner"]:::worker

        subgraph Stores["Stateful containers"]
            pg[("PostgreSQL 16 :5432")]:::db
            redis[("Redis 7 :6379")]:::db
            nats[["NATS JetStream :4222"]]:::bus
        end

        jaeger["Jaeger :16686"]:::obs
    end

    phone(["Android device"]):::ext
    tunnel(["Cloudflare tunnel"]):::ext

    dev -->|"HTTP"| web
    dev -->|"HTTP"| gw
    phone -->|"HTTPS"| tunnel
    tunnel -->|"HTTP"| gw
    web -->|"HTTP"| gw
    gw --> Services
    Services --> Stores
    workers --> Stores
    Services -.->|"OTLP :4317"| jaeger
    workers -.->|"OTLP :4317"| jaeger

    classDef edge   fill:#222,color:#fff,stroke:#aaa,stroke-width:2px,font-weight:bold
    classDef svc    fill:#1a1a1a,color:#fff,stroke:#888,stroke-width:1px
    classDef worker fill:#111,color:#fff,stroke:#666,stroke-width:1px,stroke-dasharray:3
    classDef db     fill:#0a0a0a,color:#fff,stroke:#666,stroke-width:1px
    classDef bus    fill:#111,color:#fff,stroke:#999,stroke-width:1px
    classDef obs    fill:#0d0d1a,color:#aaaaff,stroke:#4444aa,stroke-width:1px,stroke-dasharray:4
    classDef ext    fill:#222,color:#fff,stroke:#777,stroke-width:1px
```

</div>

## Containers

<div align="center">

| Container | Image or build | Published port | State |
|---|---|---|---|
| PostgreSQL | `postgres:16-alpine` | `5432` | Named volume, one schema per service |
| Redis | `redis:7-alpine` | `6379` | Named volume, locks, cache and job queue |
| NATS JetStream | `nats:2.10-alpine` | `4222`, `8222` | Named volume, durable streams |
| API Gateway | Built from `apps/api/gateway` | `8000` | Stateless |
| Domain services × 7 | Built from `apps/api/services/*` | Internal only | Stateless |
| Workers × 7 | Same images, worker entry point | None | Stateless |
| Job runner | Identity image, `worker.runner` | None | Stateless, scheduled jobs |
| Web interface | Built from `apps/app` | `3000` | Static bundle served by nginx |
| Jaeger | `jaegertracing/all-in-one` | `16686`, `4317`, `4318` | In-memory traces |

</div>

## Access paths

- **Browser.** The web interface on `3000` calls the API Gateway on `8000`.
- **Development server.** Vite on `5173` proxies `/api` and `/ws` to the API Gateway.
- **Android device.** The native shell loads the interface through a Cloudflare tunnel that
  reaches the same API Gateway, so the phone exercises the real stack over HTTPS.

## Migrations and startup

Each service applies its own migration on start, so bringing the stack up on an empty volume
creates every schema. Services expose liveness and readiness probes, and Compose waits on
them before starting the components that depend on them.
