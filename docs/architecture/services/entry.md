# Entry

> Gate control service for scanner registration and ticket validation.

## Overview

Entry is the gate control service in the platform. It registers scanner devices, validates QR tokens against a local ticket state projection, and delegates successful scans to the ticketing service. It does not issue tickets or manage ticket state.

## Responsibilities

1. Registers scanner devices and issues scanner credentials.
2. Validates QR tokens against the local ticket state projection.
3. Enforces geofence and venue constraints at scan time.
4. Forwards successful validations to ticketing via HTTP.
5. Does not issue tickets or manage ticket state.

## HTTP API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/scanners` | Register a scanner device and issue scanner credentials | Internal |

Full spec: [`docs/openapi/entry/openapi.yaml`](../openapi/entry/openapi.yaml)

> Ticket scanning is handled internally via the WebSocket gateway entry channel and the ticketing service HTTP call. There is no public scan endpoint.

## Events

### Published

| Event | NATS Subject | Description |
|-------|-------------|-------------|
| `EntryValidated` | `entry.entry.validated.v1` | Emitted when a ticket was successfully scanned and admitted. |
| `EntryRejected` | `entry.entry.rejected.v1` | Emitted when a scan attempt was rejected due to an invalid token, wrong venue, or already used ticket. |

Schemas: [`docs/openapi/entry/events/`](../openapi/entry/events/)

### Consumed

| Event | NATS Subject | Action |
|-------|-------------|--------|
| `TicketStateChanged` | `ticketing.ticket.state_changed` | Updates the local `TicketContext` projection used for scan validation. |

## Background Workers

| Worker | Type | Description |
|--------|------|-------------|
| `ticketing.ticket.state_changed` | NATS subscriber | Keeps the local ticket state projection up to date. |

## Internal Dependencies

| Package | Purpose |
|---------|---------|
| `db` | Async SQLAlchemy session factory |
| `exceptions` | Shared HTTP exception types |
| `idempotency` | Redis backed idempotency keys |
| `locking` | Redis distributed locks |
| `middleware` | Request ID, correlation, and security headers |
| `observability` | OpenTelemetry setup |

## External Dependencies

| Service | Purpose |
|---------|---------|
| PostgreSQL | Ticket state projection store |
| Redis | Idempotency keys and rate limiting |
| NATS JetStream | Consuming ticketing state change events |
| Ticketing service | HTTP call to mark a ticket as used after a valid scan |

## Key Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection string. |
| `REDIS_URL` | Redis connection URL. |
| `NATS_URL` | NATS server address. |
| `INTERNAL_API_KEY` | Shared secret for internal service-to-service calls. |
| `TICKETING_URL` | Base URL of the ticketing service. Defaults to `http://localhost:8004`. |
| `ACCESS_JWT_PRIVATE_KEY` | EC private key for user JWT verification. |
| `ACCESS_JWT_PREVIOUS_PUBLIC_KEYS` | Comma-separated previous public keys for key rotation. |
| `TICKET_QR_JWT_PRIVATE_KEY` | EC private key for QR token verification. |
| `TICKET_QR_JWT_PREVIOUS_PUBLIC_KEYS` | Previous QR JWT public keys for key rotation. |
| `SCANNER_JWT_PRIVATE_KEY` | EC private key for signing scanner credentials. |
| `SCANNER_JWT_PUBLIC_KEY` | EC public key for verifying scanner JWTs. |
| `SCANNER_TOKEN_EXPIRE_HOURS` | Scanner JWT lifetime in hours. Defaults to 12. |
| `TICKET_QR_AUDIENCE` | Expected audience claim in QR tokens. Defaults to `qrew.scan`. |
| `ENTRY_REPLAY_GRACE_SECONDS` | Grace window in seconds for duplicate QR scan detection. Defaults to 10. |
| `ENTRY_STATS_CACHE_TTL_SECONDS` | TTL in seconds for cached entry statistics. Defaults to 5. |
| `IDEMPOTENCY_ENABLED` | Flag to enable idempotency key enforcement. Defaults to true. |
| `RATELIMIT_ENABLED` | Flag to enable API rate limiting. Defaults to true. |
| `OTEL_ENABLED` | Flag to enable OpenTelemetry tracing. |
| `OTEL_ENDPOINT` | OTLP gRPC endpoint. Defaults to `http://localhost:4317`. |
