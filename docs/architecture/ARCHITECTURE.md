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

```mermaid
flowchart TB
    subgraph CL["Client Layer"]
        direction LR
        mobile(["User"])
        scanner(["Scanner Device"])
    end

    subgraph EL["Edge Layer"]
        gw["Gateway\n:8008"]
    end

    subgraph DL["Domain Layer"]
        direction LR
        id["Identity\n:8001"]
        cat["Catalog\n:8002"]
        sal["Sales\n:8003"]
        pay["Payments\n:8004"]
        tkt["Ticketing\n:8005"]
        ent["Entry\n:8006"]
        aud["Audit\n:8007"]
    end

    subgraph IL["Infrastructure Layer"]
        direction LR
        nats{{"NATS JetStream"}}
        pg[("PostgreSQL")]
        redis[("Redis")]
    end

    stripe(["Stripe"])

    mobile      -->|"HTTP"| DL
    mobile      -->|"WebSocket"| gw
    scanner     -->|"WebSocket"| gw
    scanner     -->|"HTTP"| ent

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

## Communication

The platform operates through three communication channels, each serving a distinct purpose.

* **HTTP flow.** Used by clients for all data operations such as authentication, browsing the catalog, purchasing tickets, and scanning at the gate. Each service exposes its own REST API and verifies the JWT locally without calling any other service at request time.
* **Event flow.** Used by services to propagate state changes across the platform. When a service commits a write it publishes a domain event to NATS JetStream, which other services consume asynchronously through dedicated worker processes to update their own local projections.
* **Real time flow.** Used by clients to receive live push updates without polling. The Gateway authenticates the WebSocket connection, subscribes to the relevant NATS subjects on behalf of the client, and forwards incoming messages directly over the socket for ticket status updates and gate scanning feedback.

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
    C->>S: HTTP request + JWT
    S->>S: Verify JWT locally
    S->>DB: Read or Write
    S-->>C: Response

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

