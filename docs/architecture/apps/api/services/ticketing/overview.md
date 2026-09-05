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
| `GET` | `/tickets` | List the caller's tickets | JWT |
| `GET` | `/tickets/{ticket_id}` | Get one ticket with the event it belongs to | JWT |
| `GET` | `/tickets/{ticket_id}/qr` | Get a short lived QR token for a ticket | JWT |
| `POST` | `/tickets/{ticket_id}/qr/stream` | Poll for the outcome of a QR that is being scanned | JWT |
| `POST` | `/tickets/{ticket_id}/restore` | Restore a frozen or cancelled ticket | Internal |
| `POST` | `/admission/{ticket_id}/use` | Mark a ticket as used after a successful entry scan | Internal |

Full spec: [`packages/contracts/openapi/ticketing/openapi.yaml`](../../../../../../packages/contracts/openapi/ticketing/openapi.yaml)

## Events

### Published

| Event | NATS Subject | Description |
|-------|-------------|-------------|
| `TicketStateChanged` | `ticketing.ticket.state_changed` | Emitted on every ticket state transition. Entry keeps its `TicketContext` projection from it. |
| `TicketRestored` | `ticketing.ticket.restored` | Emitted when a frozen ticket was restored onto a re-enrolled device. No service subscribes to it yet. |

Neither subject carries a `.v1` suffix, unlike every other domain subject on the platform. See [subjects.md](../../messaging/subjects.md) for the full registry.

Ticketing also publishes audit records to `audit.events.v1`.

Schemas: [`packages/contracts/openapi/ticketing/events/`](../../../../../../packages/contracts/openapi/ticketing/events/)

Every event is recorded in the `ticketing.event_outbox` table inside the same transaction as the change that caused it, and the `outbox_drainer` job publishes it afterwards. The request never talks to the broker.

### Consumed

| Event | NATS Subject | Action |
|-------|-------------|--------|
| `EventPublished` | `catalog.event.published.v1` | Upserts the `EventVenueContext` projection. |
| `EventOngoing` | `catalog.event.ongoing.v1` | Upserts the projection with the event marked as ongoing. |
| `EventCancelled` | `catalog.event.cancelled.v1` | Marks event context as cancelled and cancels issued tickets. |
| `EventDraft` | `catalog.event.draft.v1` | Upserts the projection with the event marked as draft. No service publishes this subject, so the handler never fires. |
| `DeviceAttested` | `identity.device.attested.v1` | Upserts the `DeviceContext` projection for QR binding. |
| `DeviceRevoked` | `identity.device.revoked.v1` | Upserts the device context and freezes all tickets bound to that device. |
| `ReservationCreated` | `sales.reservation.created.v1` | Creates tickets in `reserved` state. |
| `ReservationPaid` | `sales.reservation.paid.v1` | Transitions reserved tickets to `issued`. |
| `ReservationCancelled` | `sales.reservation.cancelled.v1` | Cancels reserved or issued tickets. |
| `ReservationExpired` | `sales.reservation.expired.v1` | Releases whatever the expired reservation was holding. |
| `MarketTicketFreeze` | `market.ticket.freeze.v1` | Freezes a listed ticket so it stops being usable at the door. |
| `MarketTransfer` | `market.transfer.v1` | Moves ticket ownership and holder details to the resale buyer. |
| `MarketListingExpired` | `market.listing.expired.v1` | Returns an unsold listed ticket to its holder. |

## Background Workers

| Worker | Type | Description |
|--------|------|-------------|
| `expired_ticket_purger` | arq job, daily at 04:30 | Deletes tickets that expired without ever being redeemed. |
| `scanning_reverter` | arq job, every minute | Returns a ticket left in `scanning` to `issued` once the QR it was shown for has expired, so its holder is not stuck on a processing screen. |
| `outbox_drainer` | arq job, every minute | Publishes to NATS every domain event waiting in `ticketing.event_outbox`, retrying with backoff and parking a row after eight attempts. |
| `catalog.*` | NATS subscriber | Keeps the `EventVenueContext` projection up to date. |
| `identity.*` | NATS subscriber | Keeps the `DeviceContext` projection up to date and enforces device revocation. |
| `sales.*` | NATS subscriber | Drives ticket creation and state transitions from reservation events. |
| `market.*` | NATS subscriber | Freezes listed tickets, applies resale transfers, and restores tickets whose listing expired. |

The arq jobs run in the `ticketing-arq-worker` container, which consumes the `qrew:jobs:ticketing` queue. The NATS subscribers run in the separate `ticketing-worker` container.

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
| `outbox` | Transactional outbox mixin, recorder, and drainer |
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
| `INTERNAL_API_KEY` | Shared secret for internal service to service calls. |
| `ACCESS_JWT_PRIVATE_KEY` | EC private key for user JWT verification. |
| `ACCESS_JWT_PREVIOUS_PUBLIC_KEYS` | Comma separated previous public keys for key rotation. |
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
