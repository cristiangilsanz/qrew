# Physical view

> [!NOTE]
> The physical view describes how the software maps onto machines as it stands today.

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

        workers["NATS subscribers × 5 + arq runners × 5"]:::worker

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

## Network segmentation

The stack does not run on a single flat network. `docker-compose.yml` declares three bridge networks, and a container only joins the ones it needs, so a compromised edge container cannot reach the datastores directly.

| Network | Members | Purpose |
|---|---|---|
| `publica` | `frontend`, `gateway` | The only surface that faces the outside. The web interface talks to the gateway and to nothing else. |
| `interna` | `gateway`, the seven domain services, the ten background containers, `nats`, `jaeger` | Service to service HTTP, the message broker, and trace export. The gateway reaches the services here, but never the databases. |
| `datos` | The seven domain services, the ten background containers, `postgres`, `redis` | Persistence and cache. Neither the gateway nor the frontend joins it. |

<div align="center">

```mermaid
flowchart LR
    subgraph publica["publica"]
        web["Web interface"]:::edge
        gwA["API Gateway"]:::edge
    end

    subgraph interna["interna"]
        gwB["API Gateway"]:::edge
        svcA["Domain services × 7"]:::svc
        wrkA["Background containers × 10"]:::worker
        nats[["NATS JetStream"]]:::bus
        jaeger["Jaeger"]:::obs
    end

    subgraph datos["datos"]
        svcB["Domain services × 7"]:::svc
        wrkB["Background containers × 10"]:::worker
        pg[("PostgreSQL 16")]:::db
        redis[("Redis 7")]:::db
    end

    gwA -.->|"same container"| gwB
    svcA -.->|"same containers"| svcB
    wrkA -.->|"same containers"| wrkB

    classDef edge   fill:#222,color:#fff,stroke:#aaa,stroke-width:2px,font-weight:bold
    classDef svc    fill:#1a1a1a,color:#fff,stroke:#888,stroke-width:1px
    classDef worker fill:#111,color:#fff,stroke:#666,stroke-width:1px,stroke-dasharray:3
    classDef db     fill:#0a0a0a,color:#fff,stroke:#666,stroke-width:1px
    classDef bus    fill:#111,color:#fff,stroke:#999,stroke-width:1px
    classDef obs    fill:#0d0d1a,color:#aaaaff,stroke:#4444aa,stroke-width:1px,stroke-dasharray:4
```

</div>

Only `frontend` (3000), `gateway` (8000), `postgres` (5432), `redis` (6379), `nats` (4222 and 8222) and `jaeger` (16686, 4317, 4318) publish ports to the developer host. The domain services are reachable from the host only through the gateway.

## Background containers

Ten containers run outside the request path. Five subscribe to NATS and keep local projections up to date; five are arq runners that consume a Redis job queue. All of them carry `restart: unless-stopped`.

| Container | Kind | Queue or role |
|---|---|---|
| `identity-worker` | NATS subscriber | Catalog cancellation and payment outcome notifications |
| `entry-worker` | NATS subscriber | Ticket state, event, and organisation membership projections |
| `ticketing-worker` | NATS subscriber | Catalog, identity, sales, and market projections |
| `sales-worker` | NATS subscriber | Catalog, identity, and payment projections |
| `audit-worker` | NATS subscriber | Audit record ingestion |
| `identity-arq-worker` | arq runner | `qrew:jobs:identity` |
| `catalog-worker` | arq runner | `qrew:jobs:catalog` |
| `payments-worker` | arq runner | `qrew:jobs:payments` |
| `sales-arq-worker` | arq runner | `qrew:jobs:sales` |
| `ticketing-arq-worker` | arq runner | `qrew:jobs:ticketing` |

`catalog-worker` and `payments-worker` are arq runners despite their names: they subscribe to nothing, and they only reach NATS to publish what their outbox drainer takes from the database.
