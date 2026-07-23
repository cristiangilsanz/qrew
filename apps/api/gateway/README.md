# Gateway

> API gateway — the single entry point for all client traffic. Validates JWTs at the edge, proxies HTTP requests to upstream services, and maintains WebSocket connections for real-time push updates.

## Responsibilities

- **JWT validation** — verifies every Bearer token once (ES256, kid-based rotation) and injects `X-Authenticated-User-Id` into proxied requests so upstream services trust the identity without re-verifying.
- **HTTP reverse proxy** — routes `/api/{service}/{path}` to the appropriate internal service (`identity`, `catalog`, `sales`, `payments`, `ticketing`, `entry`).
- **WebSocket hub** — authenticates WebSocket connections, subscribes to NATS JetStream on behalf of the client, and forwards messages in real time.
- **Network boundary** — the only service with a public port (`8000`). All domain services are isolated to the internal Docker network.

## Prerequisites

* Redis running and accessible
* NATS running and accessible
* All domain services running and accessible
* `uv` installed

## Setup

Copy the local configuration file and fill in the required values. Access and scanner JWT keys are required for authenticating connections.

For local development, upstream service URLs default to `http://localhost:800{1-6}` and can be overridden in `config/local.yaml`.

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
