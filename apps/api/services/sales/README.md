# Sales

> Sales service for ticket reservations, queue management, and fraud detection.

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

Start the background workers in separate terminals. `sales-worker` consumes catalog, identity and payment events to update reservation state and the local projections. `sales-arq-worker` is an arq runner on the `qrew:jobs:sales` queue that expires unpaid reservations, admits the waiting queue, assigns and expires marketplace listings, and every minute drains `sales.event_outbox`.

```bash
uv run sales-worker
uv run sales-arq-worker
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
