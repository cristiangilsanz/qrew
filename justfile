set shell := ["bash", "-c"]

IDENTITY := "services/identity"
GATE := "services/gate"
PAYMENTS := "services/payments"
CATALOG := "services/catalog"
TICKETING := "services/ticketing"
SALES := "services/sales"

default: help

# List available recipes
help:
    @just --list

# Set up dev environment from scratch
setup:
    docker compose down --volumes --rmi local --remove-orphans
    docker compose up postgres redis nats -d
    uv venv --python 3.12
    cd {{IDENTITY}} && uv sync --all-groups
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
    cd {{IDENTITY}} && uv sync --all-groups

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
    docker compose -f docker-compose.observability.yml up -d jaeger
    @echo "Jaeger UI: http://localhost:16686"

# Verify linter
lint-check:
    cd {{IDENTITY}} && uv run ruff check .

# Auto-fix linter errors
lint-fix:
    cd {{IDENTITY}} && uv run ruff check --fix .

# Verify formatter
format-check:
    cd {{IDENTITY}} && uv run ruff format --check .

# Auto-fix format errors
format-fix:
    cd {{IDENTITY}} && uv run ruff format .

# Verify type consistency
type-check:
    cd {{IDENTITY}} && uv run pyright

# Run test suite
test:
    cd {{IDENTITY}} && uv run pytest --cov=src --cov-report=term-missing --cov-report=xml -v

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

# Apply identity migrations
identity-db-upgrade:
    cd {{IDENTITY}} && uv run alembic upgrade head

# Create identity migration
identity-migrate message:
    cd {{IDENTITY}} && uv run alembic revision --autogenerate -m "{{message}}"

# Type-check identity service
identity-type-check:
    cd {{IDENTITY}} && uv run pyright

# ── Gate service ──────────────────────────────────────────────────────────────

# Run gate service with auto-reload
gate-dev:
    cd {{GATE}} && uv run dev

# Run gate NATS worker
gate-worker:
    cd {{GATE}} && uv run worker

# Apply gate migrations
gate-db-upgrade:
    cd {{GATE}} && uv run alembic upgrade head

# Create gate migration
gate-migrate message:
    cd {{GATE}} && uv run alembic revision --autogenerate -m "{{message}}"

# Type-check gate service
gate-type-check:
    cd {{GATE}} && uv run pyright

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
    cd {{TICKETING}} && uv run python -m com.qode.qrew.v1.ticketing.worker

# Apply ticketing migrations
ticketing-db-upgrade:
    cd {{TICKETING}} && uv run alembic upgrade head

# Create ticketing migration
ticketing-migrate message:
    cd {{TICKETING}} && uv run alembic revision --autogenerate -m "{{message}}"

# Type-check ticketing service
ticketing-type-check:
    cd {{TICKETING}} && uv run pyright

# Run sales service with auto-reload
sales-dev:
    cd {{SALES}} && uv run dev

# Run sales NATS worker
sales-worker:
    cd {{SALES}} && uv run python -m com.qode.qrew.v1.sales.worker

# Apply sales migrations
sales-db-upgrade:
    cd {{SALES}} && uv run alembic upgrade head

# Create sales migration
sales-migrate message:
    cd {{SALES}} && uv run alembic revision --autogenerate -m "{{message}}"

# Type-check sales service
sales-type-check:
    cd {{SALES}} && uv run pyright