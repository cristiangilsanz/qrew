# Catalog

> Catalog service for organisations, venues, events, and ticket type management.

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

Start the background worker in a separate terminal. Catalog subscribes to nothing, since it is the origin of its own data. `catalog-worker` is an arq runner on the `qrew:jobs:catalog` queue that reindexes the search view, marks an event as ongoing once its start time passes, and every minute drains `catalog.event_outbox` to publish the domain events waiting there.

```bash
uv run catalog-worker
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
