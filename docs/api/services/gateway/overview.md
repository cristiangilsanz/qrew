# Gateway

> API gateway — single entry point for all client traffic. Validates JWTs at the edge, proxies HTTP to upstream services, and maintains WebSocket connections for real-time push updates.

## Overview

Gateway is the only publicly exposed service in the platform. All HTTP and WebSocket traffic from clients passes through it. It validates Bearer JWTs once at the edge, injects `X-Authenticated-User-Id` into every proxied request, and routes traffic to the appropriate internal service. It does not persist domain state or publish domain events.

## Responsibilities

1. Validates Bearer JWTs (ES256, kid-based rotation) for all inbound HTTP and WebSocket requests.
2. Injects `X-Authenticated-User-Id` and `X-Authenticated-Token-Type` headers into proxied requests so upstream services never re-verify tokens.
3. Routes `/api/{service}/{path}` to the appropriate upstream service (identity, catalog, sales, payments, ticketing, entry).
4. Routes WebSocket connections to named channels (`entry`, `me`) and bridges NATS messages to clients.
5. Enforces public-route bypass for auth flows, health probes, and CORS preflights.
6. Manages heartbeat and keep-alive for active WebSocket connections.
7. Does not persist state or publish domain events.

## HTTP API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `*` | `/api/{service}/{path}` | Proxy any HTTP method to the named upstream service | JWT (validated at gateway) |
| `WS` | `/ws/{channel_key}` | Open a WebSocket connection to a named channel | JWT |
| `WS` | `/ws/{channel_key}` | Open a WebSocket connection as a scanner device | Scanner JWT |

Full spec: [`packages/contracts/openapi/gateway/openapi.yaml`](../../../../packages/contracts/openapi/gateway/openapi.yaml)

### Channels

| Channel | Auth | NATS subjects bridged | Description |
|---------|------|-----------------------|-------------|
| `entry` | Scanner JWT | Entry related subjects | Real time scanning updates for gate operators |
| `me` | JWT | Per user personal subjects | Personal notifications and ticket status updates |

## Events

### Published

This service does not publish domain events.

### Consumed

Gateway subscribes to NATS subjects internally per channel. The specific subjects are resolved at connection time based on the channel handler. They are not part of the standard domain event contract.

## Background Workers

This service has no background workers. All processing is driven by incoming HTTP requests.

## Internal Dependencies

| Package | Purpose |
|---------|---------|
| `exceptions` | Shared HTTP exception types |
| `idempotency` | Redis backed idempotency keys |
| `middleware` | Request ID, correlation, and security headers |
| `observability` | OpenTelemetry setup |

## External Dependencies

| Service | Purpose |
|---------|---------|
| Redis | Rate limiting and idempotency keys |
| NATS JetStream | Subscribing to subjects and forwarding messages to WebSocket clients |

## Key Configuration

| Variable | Description |
|----------|-------------|
| `NATS_URL` | NATS server address. |
| `REDIS_URL` | Redis connection URL. |
| `ACCESS_JWT_PRIVATE_KEY` | EC private key for user JWT verification. |
| `ACCESS_JWT_PREVIOUS_PUBLIC_KEYS` | Comma-separated previous public keys for key rotation. |
| `SCANNER_JWT_PRIVATE_KEY` | EC private key for scanner JWT verification. |
| `JWT_AUDIENCE` | Expected audience claim in inbound JWTs. |
| `JWT_ISSUER` | Expected issuer claim in inbound JWTs. |
| `WS_HEARTBEAT_SECONDS` | Interval in seconds between server sent ping frames. Defaults to 30. |
| `WS_PONG_TIMEOUT_SECONDS` | Time in seconds to wait for a pong before closing the connection. Defaults to 10. |
| `CORS_ORIGINS` | Allowed CORS origins as a comma separated string or JSON array. |
| `RATELIMIT_ENABLED` | Flag to enable connection rate limiting. Defaults to true. |
| `IDENTITY_URL` | Base URL of the identity service. Defaults to `http://identity:8001`. |
| `CATALOG_URL` | Base URL of the catalog service. Defaults to `http://catalog:8002`. |
| `SALES_URL` | Base URL of the sales service. Defaults to `http://sales:8003`. |
| `PAYMENTS_URL` | Base URL of the payments service. Defaults to `http://payments:8004`. |
| `TICKETING_URL` | Base URL of the ticketing service. Defaults to `http://ticketing:8005`. |
| `ENTRY_URL` | Base URL of the entry service. Defaults to `http://entry:8006`. |
| `OTEL_ENABLED` | Flag to enable OpenTelemetry tracing. |
| `OTEL_ENDPOINT` | OTLP gRPC endpoint. Defaults to `http://localhost:4317`. |
