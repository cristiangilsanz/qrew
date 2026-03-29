set shell := ["bash", "-c"]

default: help

# List available recipes
help:
    @just --list

# Set up dev environment
setup:
    docker compose down
    docker compose up postgres redis -d
    uv venv --python 3.12
    cd api && uv sync --all-groups

# Tear down dev environment
shutdown:
    docker compose down --volumes --rmi local --remove-orphans

# Install dependencies
install:
    cd api && uv sync --all-groups

# Run dev environment
dev:
    -fuser -k 8000/tcp
    cd api && uv run dev

# Verify linter
lint-check:
    cd api && uv run ruff check .

# Auto-fix linter errors
lint-fix:
    cd api && uv run ruff check --fix .

# Verify formatter
format-check:
    cd api && uv run ruff format --check .

# Auto-fix format errors
format-fix:
    cd api && uv run ruff format .

# Verify type consistency
type-check:
    cd api && uv run pyright

# Run test suite
test:
    cd api && uv run pytest --cov=src --cov-report=term-missing --cov-report=xml -v

# Auto-fix all issues
fix: lint-fix format-fix

# Verify all checks
check: lint-check format-check type-check test

# Create a new auto-generated migration
migrate message:
    cd api && uv run alembic revision --autogenerate -m "{{message}}"

# Apply all pending migrations
db-upgrade:
    cd api && uv run alembic upgrade head

# Rollback last migration
db-downgrade:
    cd api && uv run alembic downgrade -1