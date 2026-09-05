# Process view

> [!NOTE]
> The process view describes what runs concurrently and how those processes reach one another through the shared infrastructure.

<div align="center">

```mermaid
flowchart LR
    svc(["Service Process"]):::svc

    pg[("PostgreSQL")]:::db
    redis[("Redis")]:::db
    nats{{"NATS JetStream"}}:::bus
    ext(["Third-Party"]):::ext

    worker(["Worker Process"]):::worker

    svc -->|"Read / Write, outbox row included"| pg
    svc -->|"Cache / Lock"| redis
    svc -->|"Enqueue"| redis
    svc -->|"Publish, audit and fanout only"| nats

    pg -->|"Drain outbox"| worker
    nats -->|"Subscribe"| worker
    redis -->|"Dequeue"| worker
    worker -->|"Publish domain events"| nats
    worker -->|"Write"| pg
    worker -->|"Outbound"| ext

    classDef svc    fill:#222,color:#fff,stroke:#aaa,stroke-width:2px
    classDef worker fill:#111,color:#fff,stroke:#666,stroke-width:1px,stroke-dasharray:3
    classDef db     fill:#0a0a0a,color:#fff,stroke:#666,stroke-width:1px
    classDef bus    fill:#111,color:#fff,stroke:#999,stroke-width:1px
    classDef ext    fill:#222,color:#fff,stroke:#777,stroke-width:1px
```

</div>

A service process never publishes a domain event itself. It writes the event to its `event_outbox` table in the same transaction as the change, and the drainer job in its worker publishes it a moment later, so a commit and its event can never disagree. Audit records and the WebSocket fanout are the exception, since losing one costs nothing and neither carries state another service depends on.

A worker process is one of two kinds. A NATS subscriber holds durable consumers and keeps local projections up to date. An arq runner takes jobs from a Redis queue and runs the periodic work, the outbox drainer among it. Three services run one of each, four run only one.
