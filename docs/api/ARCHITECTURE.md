# Overview

## Introduction

Qrew follows an event-driven microservices architecture organised into four layers, where each service is structured internally as a layered application separating transport, domain logic, and data access.

1. **Client Layer.** Represents the external consumers of the platform.
2. **Edge Layer.** Represents the real time entry point that authenticates clients and bridges them to internal event streams.
3. **Domain Layer.** Represents the business logic of the platform.
4. **Infrastructure Layer.** Represents the shared primitives all services depend on.

Stripe is the only external third-party dependency and is integrated exclusively through the Payments service.

## Layout

The following diagram shows how the system is organised across all four layers and how each component relates to the others.

<div align="center">

```mermaid
flowchart TB
    subgraph CL["Client Layer"]
        direction LR
        mobile(["User"])
    end

    subgraph EL["Edge Layer"]
        gw["Gateway\n:8000"]
    end

    subgraph DL["Domain Layer"]
        direction LR
        id["Identity\n(internal)"]
        cat["Catalog\n(internal)"]
        sal["Sales\n(internal)"]
        pay["Payments\n(internal)"]
        tkt["Ticketing\n(internal)"]
        ent["Entry\n(internal)"]
        aud["Audit\n(internal)"]
    end

    subgraph IL["Infrastructure Layer"]
        direction LR
        nats{{"NATS JetStream"}}
        pg[("PostgreSQL")]
        redis[("Redis")]
    end

    stripe(["Stripe"])

    mobile      -->|"HTTP + WebSocket"| gw

    gw          -->|"HTTP (proxy)"| DL
    gw          -->|"Subscribe"| nats

    DL          <-->|"Events"| nats
    DL          -->|"Data"| pg
    DL          -->|"Cache / Locks"| redis

    pay         <-->|"Webhooks"| stripe

    style CL padding:20px
    style EL padding:20px
    style DL padding:20px
    style IL padding:20px
```

</div>

## Communication

The platform operates through three communication channels, each serving a distinct purpose.

* **HTTP flow.** Used by clients for all data operations such as authentication, browsing the catalog, purchasing tickets, and scanning at the gate.
* **Event flow.** Used by services to propagate state changes across the platform.
* **Real time flow.** Used by clients to receive live push updates without polling.

The following diagram shows how clients, services, and infrastructure interact across these three flows.

```mermaid
sequenceDiagram
    participant C as Client
    participant GW as Gateway
    participant S as Domain Service
    participant DB as Database
    participant NATS as NATS JetStream
    participant W as Service Worker

    Note over C,S: HTTP flow
    C->>GW: HTTP request + JWT
    GW->>GW: Verify JWT once
    GW->>S: Proxy request + X-Authenticated-User-Id
    S->>DB: Read or Write
    S-->>GW: Response
    GW-->>C: Response

    Note over S,W: Event flow
    S->>NATS: Publish domain event
    NATS->>W: Deliver event, at least once
    W->>DB: Update local projection
    W-->>NATS: Ack

    Note over C,NATS: Real time flow
    C->>GW: WebSocket + JWT
    GW->>NATS: Subscribe to client subjects
    NATS-->>GW: Message
    GW-->>C: Forward via WebSocket
```

