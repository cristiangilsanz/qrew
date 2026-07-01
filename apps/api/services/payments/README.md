# Payments

> Payments service for Stripe integration and payment lifecycle management.

## Prerequisites

* PostgreSQL running and accessible
* Redis running and accessible
* NATS running and accessible
* `uv` installed

## Setup

Copy the local configuration file and fill in the required values. A Stripe secret key and webhook signing secret are required for payment processing.

```bash
cp config/local.yaml.example config/local.yaml
```

Run database migrations.

```bash
uv run alembic upgrade head
```

Start the HTTP API.

```bash
uv run dev
```

## Tests

Run the full test suite.

```bash
uv run pytest
```

Run unit tests only.

```bash
uv run pytest -m "not integration"
```

Run integration tests. Requires PostgreSQL and Redis to be available.

```bash
uv run pytest -m integration
```
