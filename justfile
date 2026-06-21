set shell := ["bash", "-c"]

IDENTITY := "services/identity"
ENTRY := "services/entry"
PAYMENTS := "services/payments"
CATALOG := "services/catalog"
TICKETING := "services/ticketing"
SALES := "services/sales"
AUDIT := "services/audit"
GATEWAY := "gateway"

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

# Tear down dev environment
shutdown:
    docker compose down --volumes --rmi local --remove-orphans

# Install dependencies
install:
    uv sync --all-packages --all-groups

# Run dev environment
dev:
    -fuser -k 8006/tcp
    just db-upgrade
    cd {{IDENTITY}} && uv run dev

# Run background job worker
worker:
    cd {{IDENTITY}} && uv run worker

# Launch Jaeger for local trace viewing
trace:
    docker compose up -d jaeger
    @echo "Jaeger UI: http://localhost:16686"

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

# Run test suite
test:
    cd {{IDENTITY}} && uv run pytest --cov=src --cov-report=term-missing --cov-report=xml -v; code=$?; [ $code -eq 5 ] && exit 0 || exit $code

# Auto-fix all issues
fix: lint-fix format-fix

# Verify all checks
check: lint-check format-check type-check test

# Create a new auto-generated migration
migrate message:
    cd {{IDENTITY}} && uv run alembic revision --autogenerate -m "{{message}}"

# Apply all pending migrations
db-upgrade:
    cd {{IDENTITY}} && uv run alembic upgrade head

# Rollback last migration
db-downgrade:
    cd {{IDENTITY}} && uv run alembic downgrade -1

# Drop all tables and re-apply migrations from scratch
db-clean:
    cd {{IDENTITY}} && uv run alembic downgrade base && uv run alembic upgrade head

# ── Identity service ──────────────────────────────────────────────────────────

# Run identity service with auto-reload
identity-dev:
    cd {{IDENTITY}} && uv run dev

# Run identity NATS worker
identity-worker:
    cd {{IDENTITY}} && uv run worker

# Run identity Arq background job worker
identity-arq-worker:
    cd {{IDENTITY}} && uv run arq-worker

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
    cd {{ENTRY}} && uv run dev

# Run entry NATS worker
entry-worker:
    cd {{ENTRY}} && uv run worker

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
    cd {{PAYMENTS}} && uv run dev

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
    cd {{CATALOG}} && uv run dev

# Run catalog Arq worker
catalog-worker:
    cd {{CATALOG}} && uv run worker

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
    cd {{TICKETING}} && uv run dev

# Run ticketing NATS worker
ticketing-worker:
    cd {{TICKETING}} && uv run worker

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
    cd {{SALES}} && uv run dev

# Run sales NATS worker
sales-worker:
    cd {{SALES}} && uv run worker

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
    cd {{AUDIT}} && uv run dev

# Run audit NATS worker
audit-worker:
    cd {{AUDIT}} && uv run worker

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
    cd {{GATEWAY}} && uv run dev

# Type-check gateway service
gateway-type-check:
    cd {{GATEWAY}} && uv run pyright