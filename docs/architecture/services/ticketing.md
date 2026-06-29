# Ticketing

> Ticketing service for ticket lifecycle management and QR code minting.

## Overview

Ticketing is the ticket lifecycle authority in the platform. It creates and issues tickets in response to sales events, manages their states through freezing, cancellation, and restoration, and mints short lived QR tokens for physical entry. It does not perform physical scanning.

## Responsibilities

1. Creates tickets in `reserved` state when a reservation is created.
2. Transitions tickets to `issued` state when a reservation is paid.
3. Cancels tickets when a reservation is cancelled or an event is cancelled.
4. Mints short lived rotating QR tokens for physical entry.
5. Freezes tickets when a device is revoked.
6. Restores frozen or cancelled tickets when triggered by admin or policy.
7. Maintains projections of event, venue, and device data for validation.
8. Does not perform physical scanning.

## HTTP API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/tickets/{id}/qr` | Get a short lived QR token for a ticket | JWT |
| `POST` | `/tickets/{id}/qr/deny` | Deny a pending QR request | Internal |
| `POST` | `/tickets/{id}/restore` | Restore a frozen or cancelled ticket | Internal |
| `POST` | `/tickets/{id}/use` | Mark a ticket as used after a successful entry scan | Internal |

Full spec: [`docs/openapi/ticketing/openapi.yaml`](../openapi/ticketing/openapi.yaml)

## Events

### Published

| Event | NATS Subject | Description |
|-------|-------------|-------------|
| `TicketIssued` | `ticketing.ticket.issued.v1` | Emitted when a ticket was transitioned from reserved to issued. |
| `TicketFrozen` | `ticketing.ticket.frozen.v1` | Emitted when a ticket was frozen due to device revocation or policy. |
| `TicketCancelled` | `ticketing.ticket.cancelled.v1` | Emitted when a ticket was cancelled. |
| `TicketRestored` | `ticketing.ticket.restored.v1` | Emitted when a frozen or cancelled ticket was restored. |
| `TicketUsed` | `ticketing.ticket.used.v1` | Emitted when a ticket was marked as used at entry. |
| `QrMinted` | `ticketing.qr.minted.v1` | Emitted when a QR token was successfully minted. |
| `QrDenied` | `ticketing.qr.denied.v1` | Emitted when a QR token request was denied. |

Schemas: [`docs/openapi/ticketing/events/`](../openapi/ticketing/events/)

### Consumed

| Event | NATS Subject | Action |
|-------|-------------|--------|
| `EventPublished` | `catalog.event.published.v1` | Upserts the `EventVenueContext` projection. |
| `EventCancelled` | `catalog.event.cancelled.v1` | Marks event context as cancelled and cancels issued tickets. |
| `VenueCreated` | `catalog.venue.created.v1` | Upserts venue geofence and timezone into the projection. |
| `DeviceBound` | `identity.device.attested.v1` | Upserts the `DeviceContext` projection for QR binding. |
| `DeviceRevoked` | `identity.device.revoked.v1` | Upserts the device context and freezes all tickets bound to that device. |
| `ReservationCreated` | `sales.reservation.created.v1` | Creates tickets in `reserved` state. |
| `ReservationPaid` | `sales.reservation.paid.v1` | Transitions reserved tickets to `issued`. |
| `ReservationCancelled` | `sales.reservation.cancelled.v1` | Cancels reserved or issued tickets. |

## Background Workers

| Worker | Type | Description |
|--------|------|-------------|
| `catalog.*` | NATS subscriber | Keeps the `EventVenueContext` projection up to date. |
| `identity.*` | NATS subscriber | Keeps the `DeviceContext` projection up to date and enforces device revocation. |
| `sales.*` | NATS subscriber | Drives ticket creation and state transitions from reservation events. |

## Internal Dependencies

| Package | Purpose |
|---------|---------|
| `contracts` | Domain event schemas |
| `db` | Async SQLAlchemy session factory |
| `exceptions` | Shared HTTP exception types |
| `idempotency` | Redis backed idempotency keys |
| `locking` | Redis distributed locks for ticket state transitions |
| `middleware` | Request ID, correlation, and security headers |
| `observability` | OpenTelemetry setup |
| `probes` | Liveness and readiness health endpoints |
| `worker` | arq worker bootstrap |

## External Dependencies

| Service | Purpose |
|---------|---------|
| PostgreSQL | Ticket store and projection tables |
| Redis | Distributed locks, idempotency keys, and rate limiting |
| NATS JetStream | Domain event publishing and consumption |

## Key Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection string. |
| `REDIS_URL` | Redis connection URL. |
| `NATS_URL` | NATS server address. |
| `INTERNAL_API_KEY` | Shared secret for internal service-to-service calls. |
| `ACCESS_JWT_PRIVATE_KEY` | EC private key for user JWT verification. |
| `ACCESS_JWT_PREVIOUS_PUBLIC_KEYS` | Comma-separated previous public keys for key rotation. |
| `TICKET_QR_JWT_PRIVATE_KEY` | EC private key for QR token signing. |
| `TICKET_QR_JWT_PREVIOUS_PUBLIC_KEYS` | Previous QR JWT keys for key rotation. |
| `TICKET_QR_TTL_SECONDS` | QR token lifetime in seconds. Defaults to 20. |
| `TICKET_QR_REASSERT_WINDOW_SECONDS` | Window in seconds for re-asserting a QR token. Defaults to 30. |
| `TICKET_QR_AUDIENCE` | Expected audience claim in QR tokens. Defaults to `qrew.scan`. |
| `TICKET_QR_STREAM_MAX_SECONDS` | Maximum duration in seconds for a QR streaming session. Defaults to 1800. |
| `TICKET_QR_ATTESTATION_MAX_AGE_HOURS` | Maximum device attestation age in hours for QR minting. Defaults to 24. |
| `TICKET_QR_MINT_AUDIT_SAMPLE_RATE` | Fraction of QR mints written to audit, expressed as 1 in N. Defaults to 10. |
| `IDEMPOTENCY_ENABLED` | Flag to enable idempotency key enforcement. Defaults to true. |
| `RATELIMIT_ENABLED` | Flag to enable API rate limiting. Defaults to true. |
| `OTEL_ENABLED` | Flag to enable OpenTelemetry tracing. |
| `OTEL_ENDPOINT` | OTLP gRPC endpoint. Defaults to `http://localhost:4317`. |
