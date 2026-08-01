# Gateway

> Single entry point for all client traffic. Validates JWTs at the edge, proxies HTTP requests to upstream services, and maintains WebSocket connections for real-time push updates.

## Responsibilities

- JWT validation (ES256, kid-based rotation) and user identity injection into proxied requests
- HTTP reverse proxy routing `/api/{service}/{path}` to internal services
- WebSocket hub for real-time push updates via NATS JetStream subscriptions
- Network boundary — the only service with a public port (`8000`)

## Prerequisites

* Redis running and accessible
* NATS running and accessible
* All domain services running and accessible
* `uv` installed

## Setup

Copy the local configuration file and fill in the required values.

```bash
cp config/local.yaml.example config/local.yaml
```

Start the gateway.

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
