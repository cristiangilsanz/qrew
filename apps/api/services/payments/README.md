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

## Worker

Start the background worker in a separate terminal. The worker is an arq runner on the `qrew:jobs:payments` queue. It subscribes to no NATS subject; every minute it drains `payments.event_outbox` and publishes the domain events waiting there.

```bash
uv run payments-worker
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
