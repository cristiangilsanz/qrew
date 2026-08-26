# Development view

> [!NOTE]
> The development view describes how the system is organised as source code.

## **Frontend**

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

## **Backend**:

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
