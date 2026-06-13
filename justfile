set shell := ["bash", "-c"]

MONOLITH := "api"

default: help

# List available recipes
help:
    @just --list

# Set up dev environment from scratch
setup:
    docker compose down --volumes --rmi local --remove-orphans
    docker compose up postgres redis nats -d
    uv venv --python 3.12
    cd {{MONOLITH}} && uv sync --all-groups
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
    cd {{MONOLITH}} && uv sync --all-groups

# Run dev environment
dev:
    -fuser -k 8000/tcp
    just db-upgrade
    cd {{MONOLITH}} && uv run dev

# Run background job worker
worker:
    cd {{MONOLITH}} && uv run arq com.qode.qrew.v1.service.core.jobs.worker.WorkerSettings

# Launch Jaeger for local trace viewing
trace:
    docker compose -f docker-compose.observability.yml up -d jaeger
    @echo "Jaeger UI: http://localhost:16686"

# Verify linter
lint-check:
    cd {{MONOLITH}} && uv run ruff check .

# Auto-fix linter errors
lint-fix:
    cd {{MONOLITH}} && uv run ruff check --fix .

# Verify formatter
format-check:
    cd {{MONOLITH}} && uv run ruff format --check .

# Auto-fix format errors
format-fix:
    cd {{MONOLITH}} && uv run ruff format .

# Verify type consistency
type-check:
    cd {{MONOLITH}} && uv run pyright

# Run test suite
test:
    cd {{MONOLITH}} && uv run pytest --cov=src --cov-report=term-missing --cov-report=xml -v

# Auto-fix all issues
fix: lint-fix format-fix

# Verify all checks
check: lint-check format-check type-check test

# Create a new auto-generated migration
migrate message:
    cd {{MONOLITH}} && uv run alembic revision --autogenerate -m "{{message}}"

# Apply all pending migrations
db-upgrade:
    cd {{MONOLITH}} && uv run alembic upgrade head

# Rollback last migration
db-downgrade:
    cd {{MONOLITH}} && uv run alembic downgrade -1

# Drop all tables and re-apply migrations from scratch
db-clean:
    cd {{MONOLITH}} && uv run alembic downgrade base && uv run alembic upgrade head