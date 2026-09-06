# Ticketing

> Ticketing service for ticket lifecycle management and QR code minting.

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

Start the background workers in separate terminals. `ticketing-worker` consumes catalog, identity, sales and marketplace events to mint tickets and update the local projections. `ticketing-arq-worker` is an arq runner on the `qrew:jobs:ticketing` queue that purges expired tickets, returns abandoned scans to their previous state, and every minute drains `ticketing.event_outbox`.

```bash
uv run ticketing-worker
uv run ticketing-arq-worker
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
