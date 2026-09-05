# Identity

> Authentication and identity service for user registration, login, devices, and KYC.

## Prerequisites

* PostgreSQL running and accessible
* Redis running and accessible
* NATS running and accessible
* `uv` installed

## Setup

Copy the local configuration file and fill in the required values.

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

Start the background workers in separate terminals. `identity-worker` consumes catalog and payment events. `identity-arq-worker` runs the scheduled jobs, among them `outbox_drainer`, which enqueues the arq jobs waiting in `identity.outbox`, and `event_outbox_drainer`, which drains `identity.event_outbox` and publishes the domain events waiting there to NATS.

```bash
uv run identity-worker
uv run identity-arq-worker
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
