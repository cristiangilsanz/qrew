# Architecture

QREW is a mobile-first event ticketing platform built as an event-driven microservice system with a Capacitor mobile frontend.


## System Overview

```mermaid
flowchart TB
    subgraph Clients["📱 Clients"]
        app["React + Capacitor\nMobile App"]:::client
        scanner["Scanner App\nEntry Device"]:::client
    end

    subgraph Edge["🔀 Edge · :8000"]
        gw["API Gateway\nJWT validation · Reverse proxy\nRate limiting · Idempotency · CORS"]:::edge
    end

    subgraph Services["⚙️ Domain Services"]
        identity["🔑 Identity · :8001\nAuth · Users · Passkeys\nTOTP · KYC · Sessions"]:::svc
        catalog["📋 Catalog · :8002\nEvents · Venues\nOrganisations · Ticket Types"]:::svc
        sales["💸 Sales · :8003\nReservations · Resale Market\nQueue · Capacity"]:::svc
        payments["💳 Payments · :8004\nStripe · Disbursements\nRefunds"]:::svc
        ticketing["🎟️ Ticketing · :8005\nTickets · QR Tokens\nGate Policy"]:::svc
        entry["🚪 Entry · :8006\nScanner Auth\nQR Validation · Stats"]:::svc
        audit["📜 Audit · :8007\nImmutable Event Log\nAppend-only"]:::svc
    end

    subgraph Workers["🔄 Background Workers"]
        id_worker["Identity Worker\nOutbox · Email · Arq"]:::worker
        cat_worker["Catalog Worker\nOutbox · Events"]:::worker
        sales_worker["Sales Worker\nMarket Expirer · Queue"]:::worker
        tick_worker["Ticketing Worker\nNATS Subscriber"]:::worker
        pay_worker["Payments Worker\nNATS Subscriber"]:::worker
        entry_worker["Entry Worker\nNATS Subscriber"]:::worker
        audit_worker["Audit Worker\nNATS Subscriber"]:::worker
    end

    subgraph Infra["🗄️ Infrastructure"]
        pg[("🐘 PostgreSQL 16\nPrimary data store")]:::db
        redis[("🔴 Redis 7\nCache · Redlock · Arq")]:::db
        nats{{"⚡ NATS JetStream\nAt-least-once delivery"}}:::bus
        stripe(["💳 Stripe\nPayments API"]):::ext
        twilio(["📱 Twilio\nSMS · OTP"]):::ext
        maps(["🗺️ Google Maps\nVenue geocoding"]):::ext
    end

    app     -->|"HTTPS"| gw
    scanner -->|"HTTPS · Scanner JWT"| gw

    gw -->|":8001"| identity
    gw -->|":8002"| catalog
    gw -->|":8003"| sales
    gw -->|":8004"| payments
    gw -->|":8006"| entry
    gw -.->|"WebSocket · NATS sub"| nats

    identity  --> pg & redis & nats
    catalog   --> pg & nats
    sales     --> pg & redis & nats
    ticketing --> pg & nats
    payments  --> pg & nats
    entry     --> pg & redis & nats
    audit     --> pg & nats

    identity  --- id_worker
    catalog   --- cat_worker
    sales     --- sales_worker
    ticketing --- tick_worker
    payments  --- pay_worker
    entry     --- entry_worker
    audit     --- audit_worker

    payments <-->|"Webhooks"| stripe
    id_worker -->|"SMS"| twilio
    catalog   -->|"Geocode"| maps

    classDef client fill:#1a1a2e,color:#fff,stroke:#4444ff,stroke-width:2px
    classDef edge   fill:#2a2a2a,color:#fff,stroke:#888,stroke-width:2px,font-weight:bold
    classDef svc    fill:#1e2a1e,color:#fff,stroke:#4a7c4a,stroke-width:1px
    classDef worker fill:#2a1e1e,color:#fff,stroke:#7c4a4a,stroke-width:1px,stroke-dasharray:4
    classDef db     fill:#111827,color:#fff,stroke:#374151,stroke-width:1px
    classDef bus    fill:#1c1917,color:#fff,stroke:#78716c,stroke-width:1px
    classDef ext    fill:#0f172a,color:#fff,stroke:#334155,stroke-width:1px
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
