# Entry

> Gate control service for scanner registration and ticket validation.

## Prerequisites

* PostgreSQL running and accessible
* Redis running and accessible
* NATS running and accessible
* `uv` installed

## Setup

Copy the local configuration file and fill in the required values. Scanner JWT keys are required for scanner device authentication.

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

Start the background worker in a separate terminal. The worker consumes ticketing events to maintain local ticket state projections used during validation.

```bash
uv run worker
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
