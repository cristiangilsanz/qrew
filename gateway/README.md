# Gateway

> WebSocket gateway service for real time client connections and NATS message forwarding.

## Prerequisites

* Redis running and accessible
* NATS running and accessible
* `uv` installed

## Setup

Copy the local configuration file and fill in the required values. Access and scanner JWT keys are required for authenticating WebSocket connections.

```bash
cp config/local.yaml.example config/local.yaml
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

Run integration tests. Requires Redis and NATS to be available.

```bash
uv run pytest -m integration
```
