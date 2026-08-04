# Architecture

## Introduction

This document is the authoritative architectural reference for the system.

1. [Context & Scope](#context--scope)
2. [Architectural Principles](#architectural-principles)
3. [System Overview](#system-overview)
4. [Architectural Views](#architectural-views)
5. [Components Breakdown](#components-breakdown)
6. [Communication](#communication)
7. [Data Architecture](#data-architecture)
8. [Cross-Cutting Concerns](#cross-cutting-concerns)
9. [Infrastructure & Deployment](#infrastructure--deployment)

It is written for technical leads making design decisions and for engineers contributing to the codebase.

## Context & Scope

### Context

QREW is a mobile-first ticketing and event management platform covering the full operational lifecycle of a live event with fraud prevention and anti-speculation as first-class constraints.

### Scope

QREW is designed and implemented as a production-ready system that ensures the reliability characteristics expected of a deployed product.


## Architectural Principles

The following 5 software design principles shape every structural decision in the system:

<dl>
<dt>• <strong><em>Separation of Concerns.</em></strong></dt>
<dd>Every component addresses one well-defined concern and does not reach into the responsibility of another.</dd>
<dt>• <strong><em>Single Responsibility Principle.</em></strong></dt>
<dd>Every service, worker, and layer does exactly one thing, keeping each unit narrow and independently replaceable.</dd>
<dt>• <strong><em>Loose Coupling.</em></strong></dt>
<dd>Every component is independent at the code, data, and deployment level, so the failure of one does not propagate to others.</dd>
<dt>• <strong><em>Principle of Least Privilege.</em></strong></dt>
<dd>Every component is granted only the access it strictly requires to perform its function.</dd>
<dt>• <strong><em>Design for Failure.</em></strong></dt>
<dd>Every component is built under the assumption that it will eventually fail, and the system degrades gracefully when it does.</dd>
</dl>


## System Design

### High-Level Architecture

The system is organised into 6 layers:

- **Client**
- **Edge**
- **Domain**
- **Workers**
- **Infrastructure**
- **Third-Party Services**

The following diagram shows the full topology of the system:

<div align="center">

```mermaid
%%{init: {"flowchart": {"rankSpacing": 80, "nodeSpacing": 20}}}%%
flowchart TB
    subgraph Clients
        app["Mobile App"]:::client
    end

    subgraph Edge
        gw["API Gateway :8000"]:::edge
    end

    subgraph Domain
        identity["Identity :8001"]:::svc
        catalog["Catalog :8002"]:::svc
        sales["Sales :8003"]:::svc
        payments["Payments :8004"]:::svc
        ticketing["Ticketing :8005"]:::svc
        entry["Entry :8006"]:::svc
        audit["Audit :8007"]:::svc
    end

    subgraph Workers
        id_worker["Identity Worker"]:::worker
        cat_worker["Catalog Worker"]:::worker
        sales_worker["Sales Worker"]:::worker
        tick_worker["Ticketing Worker"]:::worker
        pay_worker["Payments Worker"]:::worker
        entry_worker["Entry Worker"]:::worker
        audit_worker["Audit Worker"]:::worker
    end

    subgraph Infrastructure
        pg[("PostgreSQL 16")]:::db
        redis[("Redis 7")]:::db
        nats[["NATS JetStream"]]:::bus
    end

    subgraph Third-Party Services
        stripe(["Stripe"]):::ext
        twilio(["Twilio"]):::ext
        maps(["Google Maps"]):::ext
        turnstile(["Cloudflare Turnstile"]):::ext
        hibp(["HIBP"]):::ext
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

    identity  -->|"Cache, Sessions"| redis
    sales     -->|"Locks, Counters"| redis
    entry     -->|"Locks"| redis
    id_worker -->|"Job Queue"| redis

    identity  -->|"Publish"| nats
    catalog   -->|"Publish"| nats
    sales     -->|"Publish"| nats
    entry     -->|"Publish"| nats

    nats -->|"Subscribe"| tick_worker
    nats -->|"Subscribe"| pay_worker
    nats -->|"Subscribe"| entry_worker
    nats -->|"Subscribe"| audit_worker
    nats -->|"Subscribe"| cat_worker
    nats -->|"Subscribe"| sales_worker
    nats -->|"Subscribe"| id_worker

    identity  -.-|"Spawns"| id_worker
    catalog   -.-|"Spawns"| cat_worker
    sales     -.-|"Spawns"| sales_worker
    ticketing -.-|"Spawns"| tick_worker
    payments  -.-|"Spawns"| pay_worker
    entry     -.-|"Spawns"| entry_worker
    audit     -.-|"Spawns"| audit_worker

    payments  <-->|"Webhook"| stripe
    id_worker  -->|"Send"| twilio
    catalog    -->|"Resolve"| maps
    identity   -->|"Verify"| turnstile
    identity   -->|"Check"| hibp

    app ~~~ gw
    gw ~~~ identity
    identity ~~~ id_worker
    id_worker ~~~ pg
    pg ~~~ stripe

    classDef client fill:#111,color:#fff,stroke:#fff,stroke-width:2px
    classDef edge   fill:#222,color:#fff,stroke:#aaa,stroke-width:2px,font-weight:bold
    classDef svc    fill:#1a1a1a,color:#fff,stroke:#888,stroke-width:1px
    classDef worker fill:#111,color:#fff,stroke:#666,stroke-width:1px,stroke-dasharray:3
    classDef db     fill:#0a0a0a,color:#fff,stroke:#666,stroke-width:1px
    classDef bus    fill:#111,color:#fff,stroke:#999,stroke-width:1px
    classDef ext    fill:#222,color:#fff,stroke:#777,stroke-width:1px
```

</div>

### Technology Stack

**Frontend**

[![React 19](https://img.shields.io/badge/React_19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Vite 6](https://img.shields.io/badge/Vite_6-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![TypeScript 5](https://img.shields.io/badge/TypeScript_5-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![TanStack Router](https://img.shields.io/badge/TanStack_Router-FF4154?style=for-the-badge&logo=reactrouter&logoColor=white)](https://tanstack.com/router)
[![TanStack Query](https://img.shields.io/badge/TanStack_Query-FF4154?style=for-the-badge&logo=reactquery&logoColor=white)](https://tanstack.com/query)
[![Zustand](https://img.shields.io/badge/Zustand-443E38?style=for-the-badge&logo=react&logoColor=white)](https://zustand-demo.pmnd.rs/)
[![Immer](https://img.shields.io/badge/Immer-00E7C3?style=for-the-badge&logo=javascript&logoColor=black)](https://immerjs.github.io/immer/)
[![Tailwind CSS 4](https://img.shields.io/badge/Tailwind_CSS_4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Radix UI](https://img.shields.io/badge/Radix_UI-161618?style=for-the-badge&logo=radixui&logoColor=white)](https://www.radix-ui.com/)
[![Framer Motion](https://img.shields.io/badge/Framer_Motion-0055FF?style=for-the-badge&logo=framer&logoColor=white)](https://www.framer.com/motion/)
[![Lucide React](https://img.shields.io/badge/Lucide_React-F56565?style=for-the-badge&logo=react&logoColor=white)](https://lucide.dev/)
[![React Hook Form](https://img.shields.io/badge/React_Hook_Form-EC5990?style=for-the-badge&logo=reacthookform&logoColor=white)](https://react-hook-form.com/)
[![Zod](https://img.shields.io/badge/Zod-3068B7?style=for-the-badge&logo=typescript&logoColor=white)](https://zod.dev/)
[![Axios](https://img.shields.io/badge/Axios-671DDF?style=for-the-badge&logo=axios&logoColor=white)](https://axios-http.com/)
[![react-i18next](https://img.shields.io/badge/react--i18next-26A69A?style=for-the-badge&logo=react&logoColor=white)](https://react.i18next.com/)
[![date-fns](https://img.shields.io/badge/date--fns-770C56?style=for-the-badge&logo=javascript&logoColor=white)](https://date-fns.org/)
[![react-qr-code](https://img.shields.io/badge/react--qr--code-000000?style=for-the-badge&logo=react&logoColor=white)](https://github.com/rosskhanas/react-qr-code)
[![Sonner](https://img.shields.io/badge/Sonner-000000?style=for-the-badge&logo=react&logoColor=white)](https://sonner.emilkowal.ski/)
[![Capacitor 7](https://img.shields.io/badge/Capacitor_7-119EFF?style=for-the-badge&logo=capacitor&logoColor=white)](https://capacitorjs.com/)
[![SimpleWebAuthn](https://img.shields.io/badge/SimpleWebAuthn-4A6B8A?style=for-the-badge&logo=javascript&logoColor=white)](https://simplewebauthn.dev/)
[![Stripe Elements](https://img.shields.io/badge/Stripe_Elements-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://stripe.com/docs/stripe-js)
[![Google Maps JS](https://img.shields.io/badge/@googlemaps/js--api--loader-4285F4?style=for-the-badge&logo=googlemaps&logoColor=white)](https://github.com/googlemaps/js-api-loader)
[![Cloudflare Turnstile JS](https://img.shields.io/badge/@marsidev/react--turnstile-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)](https://github.com/marsidev/react-turnstile)
[![Vitest](https://img.shields.io/badge/Vitest-6E9F18?style=for-the-badge&logo=vitest&logoColor=white)](https://vitest.dev/)
[![React Testing Library](https://img.shields.io/badge/React_Testing_Library-E33332?style=for-the-badge&logo=testinglibrary&logoColor=white)](https://testing-library.com/)
[![MSW](https://img.shields.io/badge/MSW-FF6A33?style=for-the-badge&logo=javascript&logoColor=white)](https://mswjs.io/)
[![ESLint](https://img.shields.io/badge/ESLint-4B32C3?style=for-the-badge&logo=eslint&logoColor=white)](https://eslint.org/)
[![Prettier](https://img.shields.io/badge/Prettier-F7B93E?style=for-the-badge&logo=prettier&logoColor=black)](https://prettier.io/)

**Backend**

[![Python 3.12](https://img.shields.io/badge/Python_3.12-3776AB?style=for-the-badge&logo=python&logoColor=fff)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Uvicorn](https://img.shields.io/badge/Uvicorn-499848?style=for-the-badge&logo=gunicorn&logoColor=white)](https://www.uvicorn.org/)
[![Pydantic Settings](https://img.shields.io/badge/Pydantic_Settings-E92063?style=for-the-badge&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-CC2927?style=for-the-badge&logo=postgresql&logoColor=white)](https://docs.sqlalchemy.org/)
[![asyncpg](https://img.shields.io/badge/asyncpg-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/MagicStack/asyncpg)
[![Alembic](https://img.shields.io/badge/Alembic-6BA539?style=for-the-badge&logo=postgresql&logoColor=white)](https://alembic.sqlalchemy.org/)
[![Passlib](https://img.shields.io/badge/Passlib-1C2833?style=for-the-badge&logo=python&logoColor=white)](https://passlib.readthedocs.io/)
[![argon2-cffi](https://img.shields.io/badge/argon2--cffi-1C2833?style=for-the-badge&logo=python&logoColor=white)](https://argon2-cffi.readthedocs.io/)
[![cryptography](https://img.shields.io/badge/cryptography-2C3E50?style=for-the-badge&logo=openssl&logoColor=white)](https://cryptography.io/)
[![PyJWT](https://img.shields.io/badge/PyJWT-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://pyjwt.readthedocs.io/)
[![webauthn](https://img.shields.io/badge/webauthn-1D232A?style=for-the-badge&logo=1password&logoColor=white)](https://webauthn.io/)
[![pyotp](https://img.shields.io/badge/pyotp-1C2833?style=for-the-badge&logo=python&logoColor=white)](https://pyauth.github.io/pyotp/)
[![nats-py](https://img.shields.io/badge/nats--py-27AAE1?style=for-the-badge&logo=rabbitmq&logoColor=white)](https://github.com/nats-io/nats.py)
[![arq](https://img.shields.io/badge/arq-0099CC?style=for-the-badge&logo=redis&logoColor=white)](https://arq-docs.helpmanual.io/)
[![Redlock](https://img.shields.io/badge/Redlock-FF4438?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/docs/latest/develop/use/patterns/distributed-locks/)
[![slowapi](https://img.shields.io/badge/slowapi-FF4500?style=for-the-badge&logo=fastapi&logoColor=white)](https://slowapi.readthedocs.io/)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-000000?style=for-the-badge&logo=opentelemetry&logoColor=white)](https://opentelemetry.io/)
[![structlog](https://img.shields.io/badge/structlog-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.structlog.org/)
[![geoip2](https://img.shields.io/badge/geoip2-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://geoip2.readthedocs.io/)
[![httpx](https://img.shields.io/badge/httpx-1C2833?style=for-the-badge&logo=python&logoColor=white)](https://www.python-httpx.org/)
[![pytesseract](https://img.shields.io/badge/pytesseract-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://github.com/madmaze/pytesseract)
[![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org/)
[![Pillow](https://img.shields.io/badge/Pillow-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://pillow.readthedocs.io/)
[![stripe SDK](https://img.shields.io/badge/stripe_SDK-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://github.com/stripe/stripe-python)
[![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Testcontainers](https://img.shields.io/badge/Testcontainers-291A3F?style=for-the-badge&logo=docker&logoColor=white)](https://testcontainers.com/)
[![fakeredis](https://img.shields.io/badge/fakeredis-FF4438?style=for-the-badge&logo=redis&logoColor=white)](https://github.com/cunla/fakeredis-py)
[![factory-boy](https://img.shields.io/badge/factory--boy-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://factoryboy.readthedocs.io/)
[![Ruff](https://img.shields.io/badge/Ruff-D7FF64?style=for-the-badge&logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![Pyright](https://img.shields.io/badge/Pyright-0078D4?style=for-the-badge&logo=visualstudiocode&logoColor=white)](https://github.com/microsoft/pyright)
[![uv](https://img.shields.io/badge/uv-DE5FE9?style=for-the-badge&logo=python&logoColor=white)](https://docs.astral.sh/uv/)

**Infrastructure**

[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Docker Compose](https://img.shields.io/badge/Docker_Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL_16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis 7](https://img.shields.io/badge/Redis_7-FF4438?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![NATS JetStream 2.10](https://img.shields.io/badge/NATS_JetStream_2.10-27AAE1?style=for-the-badge&logo=rabbitmq&logoColor=white)](https://docs.nats.io/nats-concepts/jetstream)
[![Jaeger](https://img.shields.io/badge/Jaeger-66CFE3?style=for-the-badge&logo=opentelemetry&logoColor=black)](https://www.jaegertracing.io/)

**Third-Party Services**

[![Stripe](https://img.shields.io/badge/Stripe-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://stripe.com/docs)
[![Twilio](https://img.shields.io/badge/Twilio-F22F46?style=for-the-badge&logo=twilio&logoColor=white)](https://www.twilio.com/docs)
[![Google Maps](https://img.shields.io/badge/Google_Maps-4285F4?style=for-the-badge&logo=googlemaps&logoColor=white)](https://developers.google.com/maps)
[![Cloudflare Turnstile](https://img.shields.io/badge/Cloudflare_Turnstile-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)](https://developers.cloudflare.com/turnstile/)
[![HIBP](https://img.shields.io/badge/HIBP-2E6DA4?style=for-the-badge&logo=haveibeenpwned&logoColor=white)](https://haveibeenpwned.com/API/v3)

**Tooling**

[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](https://docs.github.com/en/actions)
[![just](https://img.shields.io/badge/just-A52A2A?style=for-the-badge&logo=gnubash&logoColor=white)](https://just.systems/)
[![Husky](https://img.shields.io/badge/Husky-1C3148?style=for-the-badge&logo=git&logoColor=white)](https://typicode.github.io/husky/)
[![lint-staged](https://img.shields.io/badge/lint--staged-ECB22E?style=for-the-badge&logo=git&logoColor=black)](https://github.com/lint-staged/lint-staged)
[![commitlint](https://img.shields.io/badge/commitlint-000000?style=for-the-badge&logo=conventionalcommits&logoColor=white)](https://commitlint.js.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-FAB040?style=for-the-badge&logo=precommit&logoColor=black)](https://pre-commit.com/)


## Architectural Views

### Logical View

> [!NOTE]
> The logical view describes the primary domain abstractions and the bounded context decomposition of the platform.

The system is partitioned into 7 bounded contexts, each owning its own data model and enforcing its own invariants independently.

The following diagram shows every domain event flow between bounded contexts in the system:

<div align="center">

```mermaid
flowchart TB
    identity["Identity"]:::ctx
    catalog["Catalog"]:::ctx
    sales["Sales"]:::ctx
    payments["Payments"]:::ctx
    ticketing["Ticketing"]:::ctx
    entry["Entry"]:::ctx
    audit["Audit"]:::ctx

    catalog   -->|"TierAvailabilityChanged"| sales
    sales     -->|"OrderCreated"| payments
    payments  -->|"PaymentConfirmed / PaymentRefunded"| sales
    sales     -->|"OrderConfirmed"| ticketing
    payments  -->|"PaymentConfirmed / PaymentRefunded"| ticketing
    ticketing -->|"TicketIssued / TicketTransferred / TicketCancelled"| entry
    sales     -->|"OrderConfirmed"| catalog

    identity  -->|"UserRegistered / UserVerified / PasswordChanged"| audit
    catalog   -->|"EventPublished / TierAvailabilityChanged"| audit
    sales     -->|"OrderCreated / OrderConfirmed / QueueJoined / QueueAdvanced"| audit
    payments  -->|"PaymentConfirmed / PaymentRefunded"| audit
    ticketing -->|"TicketIssued / TicketTransferred / TicketCancelled"| audit
    entry     -->|"EntryGranted / EntryDenied"| audit

    classDef ctx fill:#1a1a1a,color:#fff,stroke:#888,stroke-width:1px
```

</div>

### Development View

> [!NOTE]
> The development view describes how the system is organised as source code.

#### **Frontend**

All code resides under `apps/app`, organised by feature module:

```
apps/app/
  src/
    routes/        Route Definitions
    features/      Feature Modules
    components/    Shared UI Primitives
    hooks/         Shared Hooks
    i18n/          Translations
    store/         Global State
    lib/           Utilities And Helpers
    config/        App Configuration
    assets/        Static Assets
    styles/        Global Styles
    test/          Tests
```

#### **Backend**:

All code resides under `apps/api`, with the gateway at `apps/api/gateway` and the seven domain services under `apps/api/services`, organised by an identical internal structure:

```
services/<name>/
  config/                           Environment Config
  migrations/                       Schema Migrations
  src/com/qode/qrew/v1/<name>/
    routers/                        Route Handlers
    services/                       Business Logic
    models/                         Persistence Models
    repositories/                   Data Access
    schemas/                        Request/Response Contracts
    worker/                         Background Jobs
    core/                           Shared Setup
  tests/                            Tests
```


### Process View

> [!NOTE]
> The process view describes the runtime model, covering how services and workers run as separate processes and how they communicate through shared infrastructure.

The follwoing diagram shows how services handle requests, how workers handle asynchronous work, and the communication channels each one maintains in the system:

<div align="center">

```mermaid
flowchart LR
    svc(["Service Process"]):::svc

    pg[("PostgreSQL")]:::db
    redis[("Redis")]:::db
    nats{{"NATS JetStream"}}:::bus
    ext(["Third-Party"]):::ext

    worker(["Worker Process"]):::worker

    svc -->|"Read / Write"| pg
    svc -->|"Cache / Lock"| redis
    svc -->|"Publish"| nats
    svc -->|"Enqueue"| redis

    nats -->|"Subscribe"| worker
    redis -->|"Dequeue"| worker
    worker -->|"Write"| pg
    worker -->|"Outbound"| ext

    classDef svc    fill:#222,color:#fff,stroke:#aaa,stroke-width:2px
    classDef worker fill:#111,color:#fff,stroke:#666,stroke-width:1px,stroke-dasharray:3
    classDef db     fill:#0a0a0a,color:#fff,stroke:#666,stroke-width:1px
    classDef bus    fill:#111,color:#fff,stroke:#999,stroke-width:1px
    classDef ext    fill:#222,color:#fff,stroke:#777,stroke-width:1px
```

</div>

### Physical View

> [!NOTE]
> The physical view describes how software components map to infrastructure at deployment time.

The following diagram shows the recommended production setup for the system:

<div align="center">

```mermaid
flowchart TB
    internet(["Internet"]):::ext

    subgraph Edge["Edge Layer"]
        cdn["CDN / DDoS Protection"]:::edge
        lb["Load Balancer"]:::edge
        ingress["Ingress Controller"]:::edge
    end

    subgraph Cluster["Multi-AZ Kubernetes Cluster"]
        gw["API Gateway"]:::svc

        subgraph Services["Domain Services"]
            identity["Identity"]:::svc
            catalog["Catalog"]:::svc
            sales["Sales"]:::svc
            payments["Payments"]:::svc
            ticketing["Ticketing"]:::svc
            entry["Entry"]:::svc
            audit["Audit"]:::svc
        end

        workers["Workers × 7"]:::worker

        subgraph StatefulSets["Stateful Infrastructure"]
            pg[("PostgreSQL")]:::db
            redis[("Redis")]:::db
            nats[["NATS JetStream"]]:::bus
        end

        subgraph Observability["Observability"]
            metrics["Prometheus + Grafana"]:::obs
            logs["Loki"]:::obs
            tracing["OpenTelemetry Collector"]:::obs
        end
    end

    subgraph ThirdParty["Third-Party Services"]
        stripe(["Stripe"]):::ext
        twilio(["Twilio"]):::ext
        maps(["Google Maps"]):::ext
        turnstile(["Cloudflare Turnstile"]):::ext
        hibp(["HIBP"]):::ext
    end

    internet -->|"HTTPS"| cdn
    cdn -->|"Filtered Traffic"| lb
    lb -->|"TLS Terminated"| ingress
    ingress -->|"Routed Request"| gw
    stripe -->|"Webhook"| ingress
    gw -->|"HTTP Internal"| Services
    Services -->|"Read / Write"| StatefulSets
    workers -->|"Read / Write"| StatefulSets
    workers -->|"Outbound API"| ThirdParty
    Services -.->|"Telemetry"| Observability
    workers -.->|"Telemetry"| Observability

    classDef edge   fill:#222,color:#fff,stroke:#aaa,stroke-width:2px,font-weight:bold
    classDef svc    fill:#1a1a1a,color:#fff,stroke:#888,stroke-width:1px
    classDef worker fill:#111,color:#fff,stroke:#666,stroke-width:1px,stroke-dasharray:3
    classDef db     fill:#0a0a0a,color:#fff,stroke:#666,stroke-width:1px
    classDef bus    fill:#111,color:#fff,stroke:#999,stroke-width:1px
    classDef obs    fill:#0d0d1a,color:#aaaaff,stroke:#4444aa,stroke-width:1px,stroke-dasharray:4
    classDef ext    fill:#222,color:#fff,stroke:#777,stroke-width:1px
```

</div>

The following table describes what the production deployment would recommend for each layer and element shown above, from the public internet entry point down to the external providers the platform integrates with in the system.

<div align="center">

| Component | Description |
|---|---|
| CDN / DDoS Protection | Should absorb volumetric attacks and cache static assets at the network edge before traffic reaches the cluster. |
| Load Balancer | Should serve as the cloud-managed TLS termination point, distributing inbound connections across Ingress Controller replicas. |
| Ingress Controller | Should route HTTP traffic to internal services, manage certificate lifecycle via Cert-Manager, and enforce per-route rate limiting. |
| API Gateway | Should be the sole application-level entry point, validating JWT tokens and routing each request to the correct domain service. |
| Domain Services | Should each run with a minimum of two replicas spread across availability zones, scaled individually via HPA. |
| Workers | Should run as independent deployments, one per domain service, consuming events and job queues asynchronously. |
| PostgreSQL | Should run as a primary with read replicas, fronted by PgBouncer for connection pooling and backed by daily off-cluster backups. |
| Redis | Should operate in Sentinel mode, serving distributed locking, session caching, and the asynchronous job queue. |
| NATS JetStream | Should run as a clustered deployment with stream replication, carrying all cross-context domain events durably. |
| Prometheus + Grafana | Should scrape metrics from all workloads and provide alerting rules and on-call routing. |
| Loki | Should aggregate structured logs from all workloads, indexed for query and incident investigation. |
| OpenTelemetry Collector | Should receive distributed traces from all services and forward them to a compatible tracing backend. |
| Stripe | Should handle payment processing, with outbound calls from the Payments worker and inbound webhooks through the Ingress Controller. |
| Twilio | Should deliver SMS and transactional email, called exclusively by the Identity worker. |
| Google Maps | Should provide venue geocoding, called exclusively by the Catalog service. |
| Cloudflare Turnstile | Should verify bot prevention challenge tokens at registration, called exclusively by the Identity service. |
| HIBP | Should screen credentials against the breached password database at registration and password change, called exclusively by the Identity service. |

</div>

### Scenario View

> [!NOTE]
> The scenario view illustrates key system behaviours end to end, demonstrating how the architectural layers collaborate under realistic conditions.

The following situations present representative sequences that illustrate how the architectural layers collaborate under realistic conditions, covering the 3 core flows of the system.

**User Registration**

The following sequence traces an example of the full account creation flow, from the initial client request through external verification and asynchronous email dispatch.

<div align="center">

```mermaid
sequenceDiagram
    autonumber
    participant App as Mobile App
    participant GW as API Gateway
    participant ID as Identity
    participant TS as Cloudflare Turnstile
    participant HI as HIBP
    participant PG as PostgreSQL
    participant NA as NATS JetStream
    participant RE as Redis
    participant IW as Identity Worker
    participant TW as Twilio

    App->>GW: POST /auth/register (email, password, challenge token)
    GW->>ID: Forward registration request
    ID->>TS: Verify Turnstile challenge token
    TS-->>ID: Token valid
    ID->>HI: k-anonymity prefix check (SHA-1 prefix)
    HI-->>ID: Prefix match list
    ID->>ID: Reject if password hash suffix found in list
    ID->>PG: Hash password with Argon2id and persist account
    ID->>NA: Publish UserRegistered event
    ID-->>GW: 201 Created
    GW-->>App: 201 Created
    NA-->>IW: Consume UserRegistered event
    IW->>RE: Enqueue verification email job
    IW->>TW: Dispatch verification email
```

</div>

**Ticket Purchase**

The following sequence traces the full ticket purchase flow, from order submission through distributed lock acquisition, payment initiation, webhook confirmation, and asynchronous ticket issuance.

<div align="center">

```mermaid
sequenceDiagram
    autonumber
    participant App as Mobile App
    participant GW as API Gateway
    participant SA as Sales
    participant RE as Redis
    participant PG as PostgreSQL
    participant NA as NATS JetStream
    participant PW as Payments Worker
    participant ST as Stripe
    participant PA as Payments
    participant TW as Ticketing Worker

    App->>GW: POST /orders (tier ID, quantity)
    GW->>SA: Forward order request (with X-User-ID header)
    SA->>RE: Acquire distributed lock on tier capacity (Redlock)
    RE-->>SA: Lock acquired
    SA->>PG: Validate tier availability and create order record
    SA->>RE: Release distributed lock
    SA->>NA: Publish OrderCreated event
    SA-->>GW: 202 Accepted (order ID)
    GW-->>App: 202 Accepted (order ID)
    NA-->>PW: Consume OrderCreated event
    PW->>ST: Create Stripe checkout session
    ST-->>PW: Checkout session URL
    PW->>App: Push checkout URL via WebSocket
    App->>ST: Complete payment on Stripe-hosted page
    ST->>GW: POST /webhooks/stripe (PaymentIntent confirmed)
    GW->>PA: Forward webhook
    PA->>NA: Publish PaymentConfirmed event
    NA-->>TW: Consume PaymentConfirmed event
    TW->>PG: Generate QR code and persist ticket
    TW->>App: Push ticket issuance confirmation via WebSocket
```

</div>

**Entry Scanning**

The following sequence traces the admission flow, from QR code scan at the venue through capacity enforcement, event publishing, and real-time confirmation.

<div align="center">

```mermaid
sequenceDiagram
    autonumber
    participant Org as Organiser App
    participant GW as API Gateway
    participant EN as Entry
    participant RE as Redis
    participant PG as PostgreSQL
    participant NA as NATS JetStream
    participant AW as Audit Worker

    Org->>GW: POST /entry/scan (QR code payload)
    GW->>EN: Forward scan request (with X-User-ID header)
    EN->>PG: Validate ticket against local read model
    PG-->>EN: Ticket valid and not yet used
    EN->>RE: Acquire distributed lock on venue capacity (Redlock)
    RE-->>EN: Lock acquired
    EN->>PG: Increment venue capacity counter and persist EntryGranted record
    EN->>RE: Release distributed lock
    EN->>NA: Publish EntryGranted event
    EN-->>GW: 200 OK (admission result)
    GW-->>Org: 200 OK (admission result)
    NA-->>AW: Consume EntryGranted event
    AW->>PG: Append immutable audit log entry
```

</div>

## Components Breakdown

### Frontend

- [App](../apps/app/overview.md)

### Backend

#### API Gateway

- [Gateway](../apps/api/services/gateway/overview.md)

#### Domain Services

- [Identity](../apps/api/services/identity/overview.md)
- [Catalog](../apps/api/services/catalog/overview.md)
- [Sales](../apps/api/services/sales/overview.md)
- [Payments](../apps/api/services/payments/overview.md)
- [Ticketing](../apps/api/services/ticketing/overview.md)
- [Entry](../apps/api/services/entry/overview.md)
- [Audit](../apps/api/services/audit/overview.md)


## Communication

### APIs

- **Style:** REST
- **Format:** JSON
- **Versioning:** `/v1`
- **Auth:** Bearer token

### Protocols

<div align="center">

```mermaid
flowchart LR
    client["Mobile App"]
    gw["API Gateway"]
    services["Domain Services"]
    nats["NATS JetStream"]
    infra["Infrastructure"]

    client   -->|"HTTPS · WebSocket"| gw
    gw       -->|"HTTP"| services
    services -->|"Pub/Sub"| nats
    nats     -->|"Pub/Sub"| services
    services -->|"TCP"| infra
```

</div>

### Internal Communication

#### Event Messaging

- **Broker:** NATS JetStream
- **Delivery:** At-least-once
- **Subject format:** `<context>.<entity>.<event>`
- **Envelope:** `<type> | <version> | <timestamp> | <service> | <correlation_id>`
- **Acknowledgment:** On success
- **Failure:** Retry

### External Interfaces

| Provider | Protocol | Direction |
|---|---|---|
| Stripe | REST · Webhook | Bidirectional |
| Twilio | REST | Outbound |
| Google Maps | REST | Outbound |
| Cloudflare Turnstile | REST | Outbound |
| HIBP | REST · K-Anonymity | Outbound |

## Data Architecture

### Data Ownership

<dl>
<dt>• <strong><em>Schema Isolation.</em></strong></dt>
<dd>Each service owns a dedicated PostgreSQL schema, shared with no other service.</dd>
<dt>• <strong><em>Autonomous Evolution.</em></strong></dt>
<dd>Each service manages its own Alembic migration history independently.</dd>
<dt>• <strong><em>Exclusive Write Authority.</em></strong></dt>
<dd>Each service is the sole writer to its own schema.</dd>
<dt>• <strong><em>No Cross-Service Reads.</em></strong></dt>
<dd>Each service accesses foreign data exclusively through published domain events, never by querying another service's schema directly.</dd>
<dt>• <strong><em>Event-Driven Projection.</em></strong></dt>
<dd>Each service projects the read models it needs from domain events into its own schema.</dd>
<dt>• <strong><em>Eventual Consistency.</em></strong></dt>
<dd>Each service boundary is kept consistent asynchronously through the event stream, without distributed transactions.</dd>
</dl>

### Data Storage

| Store | Technology | Role |
|---|---|---|
| Primary Database | PostgreSQL 16 | Transactional State |
| Cache / Queue / Lock | Redis 7 | Session Cache · Redlock Distributed Locks · Arq Job Queue  |
| Message Bus | NATS JetStream | Durable Event Streaming |


### Data Model

The following documents describe the database schema for each bounded context in the system:

- [Identity](../apps/api/services/identity/schema.md)
- [Catalog](../apps/api/services/catalog/schema.md)
- [Sales](../apps/api/services/sales/schema.md)
- [Payments](../apps/api/services/payments/schema.md)
- [Ticketing](../apps/api/services/ticketing/schema.md)
- [Entry](../apps/api/services/entry/schema.md)
- [Audit](../apps/api/services/audit/schema.md)


### Data Flow

<div align="center">

```mermaid
sequenceDiagram
    participant App
    participant Gateway
    participant Service
    participant PostgreSQL
    participant Redis
    participant NATS
    participant Worker
    participant ThirdParty

    Note over App, PostgreSQL: HTTP Flow
    App->>Gateway: HTTPS request
    Gateway->>Gateway: Validate JWT
    Gateway->>Gateway: Inject Identity Headers
    Gateway->>Service: Forward request
    Service->>PostgreSQL: Read / Write
    Service->>Redis: Cache / Lock
    Service-->>App: Response

    Note over App, Gateway: WebSocket Flow
    App->>Gateway: Upgrade connection
    Worker->>Gateway: Emit notification
    Gateway-->>App: Push to client

    Note over Service, Worker: Event Flow
    Service->>PostgreSQL: Write state
    Service->>NATS: Publish domain event
    NATS->>Worker: Deliver event
    Worker->>PostgreSQL: Write projected state
    Worker->>Redis: Invalidate cache

    Note over ThirdParty, Worker: Webhook Flow
    ThirdParty->>Gateway: POST webhook
    Gateway->>Service: Forward
    Service->>NATS: Publish domain event
    NATS->>Worker: Deliver event
    Worker->>PostgreSQL: Write state

    Note over Service, ThirdParty: Outbound Integration Flow
    Service->>ThirdParty: API call
    ThirdParty-->>Service: Response
    Service->>PostgreSQL: Persist result

    Note over Worker, ThirdParty: Background Job Flow
    Service->>Redis: Enqueue job
    Worker->>Redis: Dequeue job
    Worker->>ThirdParty: Execute outbound task
    Worker->>PostgreSQL: Write result
```

</div>

## Cross-Cutting Concerns

### Security

The full dive into the topic is in [Security](cross-cutting/security.md).

### Observability

The full dive into the topic is in [Observability](cross-cutting/observability.md).

## Infrastructure & Deployment

<div align="center">

*⏳ Pending...*

</div>


