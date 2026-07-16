set shell := ["bash", "-c"]

IDENTITY := "apps/api/services/identity"
ENTRY := "apps/api/services/entry"
PAYMENTS := "apps/api/services/payments"
CATALOG := "apps/api/services/catalog"
TICKETING := "apps/api/services/ticketing"
SALES := "apps/api/services/sales"
AUDIT := "apps/api/services/audit"
GATEWAY := "apps/api/gateway"

PKG_IDEMPOTENCY   := "packages/shared-python/idempotency"
PKG_RATELIMIT     := "packages/shared-python/ratelimit"
PKG_LOCKING       := "packages/shared-python/locking"
PKG_PAGINATION    := "packages/shared-python/pagination"
PKG_JOBS          := "packages/shared-python/jobs"
PKG_DB            := "packages/shared-python/db"
PKG_EXCEPTIONS    := "packages/shared-python/exceptions"
PKG_MIDDLEWARE    := "packages/shared-python/middleware"
PKG_OBSERVABILITY := "packages/shared-python/observability"
PKG_PROBES        := "packages/shared-python/probes"
PKG_SECURITY      := "packages/shared-python/security"
PKG_AUDITOR       := "packages/shared-python/auditor"

default: help

# List available recipes
help:
    @just --list

# Set up dev environment from scratch
setup:
    docker compose down --volumes --rmi local --remove-orphans
    docker compose up postgres redis nats -d
    uv venv --python 3.12
    uv sync --all-packages --all-groups
    just db-upgrade

# Stop dev environment
stop:
    docker compose stop

# Resume dev environment
resume:
    docker compose start postgres redis nats
    just db-upgrade

# Build and run all services in containers
up:
    docker compose up postgres redis nats -d --wait
    just db-upgrade
    docker compose up --build -d
    docker compose logs -f

# Tear down dev environment
shutdown:
    docker compose down --volumes --rmi local --remove-orphans

# Apply pending migrations for all services
db-upgrade:
    cd {{IDENTITY}}  && uv run alembic upgrade head
    cd {{ENTRY}}     && uv run alembic upgrade head
    cd {{PAYMENTS}}  && uv run alembic upgrade head
    cd {{CATALOG}}   && uv run alembic upgrade head
    cd {{TICKETING}} && uv run alembic upgrade head
    cd {{SALES}}     && uv run alembic upgrade head
    cd {{AUDIT}}     && uv run alembic upgrade head

# Rollback last migration for all services
db-downgrade:
    cd {{IDENTITY}}  && uv run alembic downgrade -1
    cd {{ENTRY}}     && uv run alembic downgrade -1
    cd {{PAYMENTS}}  && uv run alembic downgrade -1
    cd {{CATALOG}}   && uv run alembic downgrade -1
    cd {{TICKETING}} && uv run alembic downgrade -1
    cd {{SALES}}     && uv run alembic downgrade -1
    cd {{AUDIT}}     && uv run alembic downgrade -1

# Wipe and re-apply all migrations from scratch
db-clean:
    cd {{IDENTITY}}  && uv run alembic downgrade base && uv run alembic upgrade head
    cd {{ENTRY}}     && uv run alembic downgrade base && uv run alembic upgrade head
    cd {{PAYMENTS}}  && uv run alembic downgrade base && uv run alembic upgrade head
    cd {{CATALOG}}   && uv run alembic downgrade base && uv run alembic upgrade head
    cd {{TICKETING}} && uv run alembic downgrade base && uv run alembic upgrade head
    cd {{SALES}}     && uv run alembic downgrade base && uv run alembic upgrade head
    cd {{AUDIT}}     && uv run alembic downgrade base && uv run alembic upgrade head

# Install dependencies
install:
    uv sync --all-packages --all-groups

# Launch Jaeger for local trace viewing
trace:
    docker compose up -d jaeger
    @echo "Jaeger UI: http://localhost:16686"

# Export OpenAPI specs for all services to docs/openapi/
export-openapi:
    bash scripts/export-openapi.sh

# Verify linter
lint-check:
    uv run ruff check .

# Auto-fix linter errors
lint-fix:
    uv run ruff check --fix .

# Verify formatter
format-check:
    uv run ruff format --check .

# Auto-fix format errors
format-fix:
    uv run ruff format .

# Verify type consistency (all services)
type-check:
    cd {{IDENTITY}} && uv run pyright
    cd {{ENTRY}} && uv run pyright
    cd {{PAYMENTS}} && uv run pyright
    cd {{CATALOG}} && uv run pyright
    cd {{TICKETING}} && uv run pyright
    cd {{SALES}} && uv run pyright
    cd {{AUDIT}} && uv run pyright
    cd {{GATEWAY}} && uv run pyright

# Run test suite (all services and packages)
test:
    #!/usr/bin/env bash
    set -e
    _run() { cd "$1" && uv run pytest tests/unit/ -v; cd - > /dev/null; }
    _run {{AUDIT}}
    _run {{CATALOG}}
    _run {{ENTRY}}
    _run {{PAYMENTS}}
    _run {{SALES}}
    _run {{TICKETING}}
    _run {{IDENTITY}}
    _run {{PKG_IDEMPOTENCY}}
    _run {{PKG_RATELIMIT}}
    _run {{PKG_LOCKING}}
    _run {{PKG_PAGINATION}}
    _run {{PKG_JOBS}}
    _run {{PKG_DB}}
    _run {{PKG_EXCEPTIONS}}
    _run {{PKG_MIDDLEWARE}}
    _run {{PKG_OBSERVABILITY}}
    _run {{PKG_PROBES}}
    _run {{PKG_SECURITY}}
    _run {{PKG_AUDITOR}}

# Auto-fix all issues
fix: lint-fix format-fix

# Verify all checks
check: lint-check format-check type-check test

# ── Identity service ──────────────────────────────────────────────────────────

# Run identity service with auto-reload
identity-dev:
    cd {{IDENTITY}} && uv run alembic upgrade head && uv run identity-dev

# Run identity NATS worker
identity-worker:
    cd {{IDENTITY}} && uv run identity-worker

# Run identity Arq background job worker
identity-arq-worker:
    cd {{IDENTITY}} && uv run identity-arq-worker

# Apply identity migrations
identity-db-upgrade:
    cd {{IDENTITY}} && uv run alembic upgrade head

# Create identity migration
identity-migrate message:
    cd {{IDENTITY}} && uv run alembic revision --autogenerate -m "{{message}}"

# Type-check identity service
identity-type-check:
    cd {{IDENTITY}} && uv run pyright

# ── Entry service ─────────────────────────────────────────────────────────────

# Run entry service with auto-reload
entry-dev:
    cd {{ENTRY}} && uv run alembic upgrade head && uv run entry-dev

# Run entry NATS worker
entry-worker:
    cd {{ENTRY}} && uv run entry-worker

# Apply entry migrations
entry-db-upgrade:
    cd {{ENTRY}} && uv run alembic upgrade head

# Create entry migration
entry-migrate message:
    cd {{ENTRY}} && uv run alembic revision --autogenerate -m "{{message}}"

# Type-check entry service
entry-type-check:
    cd {{ENTRY}} && uv run pyright

# ── Payments service ──────────────────────────────────────────────────────────

# Run payments service with auto-reload
payments-dev:
    cd {{PAYMENTS}} && uv run alembic upgrade head && uv run payments-dev

# Apply payments migrations
payments-db-upgrade:
    cd {{PAYMENTS}} && uv run alembic upgrade head

# Create payments migration
payments-migrate message:
    cd {{PAYMENTS}} && uv run alembic revision --autogenerate -m "{{message}}"

# Type-check payments service
payments-type-check:
    cd {{PAYMENTS}} && uv run pyright

# ── Catalog service ───────────────────────────────────────────────────────────

# Run catalog service with auto-reload
catalog-dev:
    cd {{CATALOG}} && uv run alembic upgrade head && uv run catalog-dev

# Run catalog Arq worker
catalog-worker:
    cd {{CATALOG}} && uv run catalog-worker

# Apply catalog migrations
catalog-db-upgrade:
    cd {{CATALOG}} && uv run alembic upgrade head

# Create catalog migration
catalog-migrate message:
    cd {{CATALOG}} && uv run alembic revision --autogenerate -m "{{message}}"

# Type-check catalog service
catalog-type-check:
    cd {{CATALOG}} && uv run pyright

# ── Ticketing service ─────────────────────────────────────────────────────────

# Run ticketing service with auto-reload
ticketing-dev:
    cd {{TICKETING}} && uv run alembic upgrade head && uv run ticketing-dev

# Run ticketing NATS worker
ticketing-worker:
    cd {{TICKETING}} && uv run ticketing-worker

# Apply ticketing migrations
ticketing-db-upgrade:
    cd {{TICKETING}} && uv run alembic upgrade head

# Create ticketing migration
ticketing-migrate message:
    cd {{TICKETING}} && uv run alembic revision --autogenerate -m "{{message}}"

# Type-check ticketing service
ticketing-type-check:
    cd {{TICKETING}} && uv run pyright

# ── Sales service ─────────────────────────────────────────────────────────────

# Run sales service with auto-reload
sales-dev:
    cd {{SALES}} && uv run alembic upgrade head && uv run sales-dev

# Run sales NATS worker
sales-worker:
    cd {{SALES}} && uv run sales-worker

# Apply sales migrations
sales-db-upgrade:
    cd {{SALES}} && uv run alembic upgrade head

# Create sales migration
sales-migrate message:
    cd {{SALES}} && uv run alembic revision --autogenerate -m "{{message}}"

# Type-check sales service
sales-type-check:
    cd {{SALES}} && uv run pyright

# ── Audit service ─────────────────────────────────────────────────────────────

# Run audit service with auto-reload
audit-dev:
    cd {{AUDIT}} && uv run alembic upgrade head && uv run audit-dev

# Run audit NATS worker
audit-worker:
    cd {{AUDIT}} && uv run audit-worker

# Apply audit migrations
audit-db-upgrade:
    cd {{AUDIT}} && uv run alembic upgrade head

# Create audit migration
audit-migrate message:
    cd {{AUDIT}} && uv run alembic revision --autogenerate -m "{{message}}"

# Type-check audit service
audit-type-check:
    cd {{AUDIT}} && uv run pyright

# ── Gateway service ───────────────────────────────────────────────────────────

# Run gateway service with auto-reload
gateway-dev:
    cd {{GATEWAY}} && uv run gateway-dev

# Type-check gateway service
gateway-type-check:
    cd {{GATEWAY}} && uv run pyright

# Forward Stripe webhooks to local payments service (copy the whsec_ key to payments config/local.yaml)
stripe-dev:
    stripe listen --forward-to localhost:8004/v1/webhooks/stripe