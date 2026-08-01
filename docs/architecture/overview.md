# Architecture

QREW is a mobile-first event ticketing platform built as an event-driven microservice system with a Capacitor mobile frontend.


## System Overview

```mermaid
flowchart TB
    subgraph Clients
        app["Mobile App\nReact 19 + Capacitor\nAttendee, Scanner, Organiser roles"]:::client
    end

    subgraph Edge
        gw["API Gateway :8000\nJWT validation, reverse proxy\nRate limiting, idempotency, CORS\nWebSocket hub"]:::edge
    end

    subgraph Services
        identity["Identity :8001\nAuthentication, users, sessions\nPasskeys, TOTP, KYC, PII"]:::svc
        catalog["Catalog :8002\nEvents, venues, organisations\nTicket types"]:::svc
        sales["Sales :8003\nReservations, capacity\nResale market, queue"]:::svc
        payments["Payments :8004\nStripe integration\nDisbursements, refunds"]:::svc
        ticketing["Ticketing :8005\nTicket issuance, QR tokens\nGate policy evaluation"]:::svc
        entry["Entry :8006\nScanner authentication\nQR validation, entry stats"]:::svc
        audit["Audit :8007\nImmutable audit log\nAppend-only"]:::svc
    end

    subgraph Workers
        id_worker["identity-worker\nTransactional outbox\nEmail dispatch, Arq jobs"]:::worker
        cat_worker["catalog-worker\nTransactional outbox"]:::worker
        sales_worker["sales-worker\nMarket expirer\nQueue processor"]:::worker
        tick_worker["ticketing-worker\nNATS subscriber"]:::worker
        pay_worker["payments-worker\nNATS subscriber"]:::worker
        entry_worker["entry-worker\nNATS subscriber"]:::worker
        audit_worker["audit-worker\nNATS subscriber"]:::worker
    end

    subgraph Infrastructure
        pg[("PostgreSQL 16\nOne schema per service")]:::db
        redis[("Redis 7\nCache, Redlock, Arq queues")]:::db
        nats[["NATS JetStream\nAt-least-once delivery\nPersisted streams"]]:::bus
    end

    subgraph External
        stripe(["Stripe\nPayments API"]):::ext
        twilio(["Twilio\nSMS and OTP"]):::ext
        maps(["Google Maps\nVenue geocoding"]):::ext
    end

    app -->|"HTTPS + WebSocket"| gw

    gw -->|"HTTP :8001"| identity
    gw -->|"HTTP :8002"| catalog
    gw -->|"HTTP :8003"| sales
    gw -->|"HTTP :8004"| payments
    gw -->|"HTTP :8006"| entry

    identity  -->|"Read/Write"| pg
    catalog   -->|"Read/Write"| pg
    sales     -->|"Read/Write"| pg
    ticketing -->|"Read/Write"| pg
    payments  -->|"Read/Write"| pg
    entry     -->|"Read/Write"| pg
    audit     -->|"Write"| pg

    identity  -->|"Cache, sessions"| redis
    sales     -->|"Locks, counters"| redis
    entry     -->|"Locks"| redis
    id_worker -->|"Arq job queue"| redis

    identity  -->|"Publish events"| nats
    catalog   -->|"Publish events"| nats
    sales     -->|"Publish events"| nats
    entry     -->|"Publish events"| nats

    nats -->|"Subscribe"| tick_worker
    nats -->|"Subscribe"| pay_worker
    nats -->|"Subscribe"| entry_worker
    nats -->|"Subscribe"| audit_worker
    nats -->|"Subscribe"| cat_worker
    nats -->|"Subscribe"| sales_worker
    nats -->|"Subscribe"| id_worker

    identity  -.-|"spawns"| id_worker
    catalog   -.-|"spawns"| cat_worker
    sales     -.-|"spawns"| sales_worker
    ticketing -.-|"spawns"| tick_worker
    payments  -.-|"spawns"| pay_worker
    entry     -.-|"spawns"| entry_worker
    audit     -.-|"spawns"| audit_worker

    payments <-->|"Webhooks"| stripe
    id_worker  -->|"SMS, OTP"| twilio
    catalog    -->|"Geocode"| maps

    classDef client fill:#1e293b,color:#f1f5f9,stroke:#475569,stroke-width:2px
    classDef edge   fill:#1e1e1e,color:#f1f5f9,stroke:#6b7280,stroke-width:2px,font-weight:bold
    classDef svc    fill:#14292c,color:#f1f5f9,stroke:#2d6a4f,stroke-width:1px
    classDef worker fill:#2a1f1f,color:#f1f5f9,stroke:#7c3535,stroke-width:1px,stroke-dasharray:3
    classDef db     fill:#0f172a,color:#f1f5f9,stroke:#334155,stroke-width:1px
    classDef bus    fill:#1c1917,color:#f1f5f9,stroke:#57534e,stroke-width:1px
    classDef ext    fill:#1a1a2e,color:#f1f5f9,stroke:#4a4a6a,stroke-width:1px
```


## Layers

**Client layer.** The React and Capacitor app is the only external consumer. All requests flow through the gateway. No service is directly reachable from outside.

**Edge layer.** The gateway validates JWT tokens on every request and injects `X-Authenticated-User-Id` and `X-Authenticated-User-Is-Admin` headers before proxying to services. Services trust these headers and do not re-verify tokens.

**Domain layer.** Seven independent services, each owning its own PostgreSQL schema and communicating with other services exclusively via NATS JetStream events. No direct service-to-service HTTP calls.

**Infrastructure layer.** PostgreSQL for persistence, NATS JetStream for at-least-once event delivery, Redis for distributed locks via Redlock, rate-limit counters, and background job queues via Arq.


## Communication Patterns

| Pattern | Transport | Used for |
|---|---|---|
| Request/response | HTTP via gateway | All client-initiated operations |
| Domain events | NATS JetStream | State propagation between services |
| Real-time push | WebSocket via gateway | Queue position updates, live notifications |
| Background jobs | Redis + Arq | Scheduled tasks: email, cleanup, token rotation |


## Auth Model

- Tokens are signed with ES256 asymmetric signing. The identity service signs. All other services only verify.
- The gateway decodes the token once and forwards the user identity as trusted headers. Services never see raw tokens.
- Access tokens carry an `adm` claim for admin users, propagated as `X-Authenticated-User-Is-Admin: 1`.
- Scanner tokens are a separate token type issued by the entry service, validated independently by the gateway.


## Service Responsibilities

| Service | Owns | Key rules |
|---|---|---|
| **Identity** | Users, sessions, passkeys, KYC, TOTP | PII encrypted at rest with Fernet. Passwords hashed with Argon2. |
| **Catalog** | Events, venues, organisations, ticket types | Org creation requires `is_admin`. Ongoing events are immutable. |
| **Sales** | Reservations, market listings, queue | Per-user ticket limits enforced server-side. Market 24h cutoff enforced server-side. |
| **Ticketing** | Tickets, QR tokens | Tickets are issued from paid reservations via NATS event. |
| **Payments** | Payment intents, Stripe webhooks | Stripe is the only external dependency. |
| **Entry** | Scanners, scan records | QR scanning only permitted for ongoing events. |
| **Audit** | Immutable audit log | Write only. Consumes events from all other services. |


## Detailed Docs

- [API architecture](docs/api/ARCHITECTURE.md): service internals, communication flows, NATS subjects
- [Service docs](docs/api/services/): per-service schema, events, and overview
- [App architecture](docs/app/ARCHITECTURE.md): frontend stack, folder structure, Capacitor setup
- [Development guides](docs/development/): local setup, Docker, mobile builds, testing
