# Gateway

> WebSocket gateway for real time client connections and NATS message forwarding.

## Overview

Gateway is the real time WebSocket edge service in the platform. It authenticates WebSocket connections via JWT, routes them to named channels, and forwards internal NATS messages to connected clients. It does not persist state, call other services, or publish domain events.

## Responsibilities

1. Authenticates WebSocket connections via user access tokens or scanner tokens.
2. Routes connections to named channels including `entry` and `me`.
3. Subscribes to NATS subjects on behalf of the connected client.
4. Forwards NATS messages to connected WebSocket clients.
5. Manages heartbeat and connection keep alive for active connections.
6. Does not persist state, call other services, or publish domain events.

## HTTP API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `WS` | `/ws/{channel_key}` | Open a WebSocket connection to a named channel | JWT |
| `WS` | `/ws/{channel_key}` | Open a WebSocket connection as a scanner device | Scanner JWT |

Full spec: [`docs/openapi/gateway/openapi.yaml`](../openapi/gateway/openapi.yaml)

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
| `OTEL_ENABLED` | Flag to enable OpenTelemetry tracing. |
| `OTEL_ENDPOINT` | OTLP gRPC endpoint. Defaults to `http://localhost:4317`. |
