# Development view

> [!NOTE]
> The development view describes how the source code is laid out and what each part depends on.

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

```
apps/api/services/<name>/
  config/                           Environment Config
  migrations/                       Schema Migrations
  src/com/qode/qrew/v1/<name>/
    routers/                        Route Handlers
    services/                       Business Logic
    models/                         Persistence Models
    repositories/                   Data Access
    schemas/                        Request/Response Contracts
    worker/
      jobs/                         Periodic And Queued Jobs
      subscribers/                  NATS Consumers
    core/                           Shared Setup
  tests/                            Tests
```

```
apps/api/gateway/
  src/com/qode/qrew/v1/gateway/
    routers/                        Health And Fanout Routes
    proxy/                          Request Forwarding
    middleware/                     Authentication And Headers
    hub/                            WebSocket Connection Hub
    channels/                       Channel Key Resolution
    clients/                        NATS Client
    core/                           Shared Setup
```

```
packages/
  contracts/
    src/contracts/
      events/                       Domain Event Payload Shapes
      messaging/                    Envelope
    openapi/                        Generated Specs And Event Schemas
  shared-python/
    db, exceptions, idempotency, jobs, locking, messaging, middleware,
    observability, outbox, pagination, probes, ratelimit, security, worker
  shared-ts/                        Reserved, currently empty
```

Every service depends on `contracts` and on the shared Python packages it needs, and never on another service's source. The few runtime calls one service makes to another go over HTTP and are listed in the [logical view](logical.md). The `outbox` package holds the transactional outbox mixin, its recorder and its drainer, so the five services that publish domain events share one table shape and one set of retry semantics.
