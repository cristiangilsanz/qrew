# Sales

> Sales service for reservation management and fraud detection.

## Overview

Sales is the reservation and queue management service in the platform. It creates reservations with distributed inventory locking, manages the waitlist queue for sold-out events, scores reservation attempts for fraud, and settles paid reservations in response to payment events. It does not create or issue tickets.

## Responsibilities

1. Creates ticket reservations with distributed inventory locking.
2. Expires reservations via background sweep when the TTL elapses.
3. Manages queue join and admission for sold-out events.
4. Scores reservation attempts for fraud using device fingerprint, IP velocity, account age, time to purchase, and VoIP phone carrier signals.
5. Settles paid reservations in response to payment events.
6. Maintains projections of catalog events and identity signals for availability and fraud decisions.
7. Does not create or issue tickets.

## HTTP API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/events/{event_id}/queue/join` | Join the admission queue for an event | JWT |
| `GET` | `/events/{event_id}/queue/position` | Get the caller's place in the admission queue | JWT |
| `POST` | `/events/{event_id}/queue/redeem` | Redeem an admitted turn for a reservation window | JWT |
| `POST` | `/events/{event_id}/reserve` | Create a reservation covering one or more ticket types of the event | JWT |
| `GET` | `/reservations/{reservation_id}` | Get reservation status and the tiers it covers | JWT |
| `PUT` | `/reservations/{reservation_id}/holders` | Set the holder of each reserved seat | JWT |
| `POST` | `/reservations/{reservation_id}/cancel` | Cancel the reservation | JWT |
| `POST` | `/billing/reservations/{reservation_id}/charge` | Charge the reservation | JWT |
| `POST` | `/tickets/{ticket_id}/market/list` | List a ticket for resale | JWT |
| `GET` | `/tickets/{ticket_id}/market/listing` | Get the active listing for a ticket | JWT |
| `POST` | `/events/{event_id}/market/queue/join` | Join the market resale queue for an event | JWT |
| `GET` | `/events/{event_id}/market/queue/status` | Check resale queue position and pending assignment | JWT |
| `DELETE` | `/events/{event_id}/market/queue/leave` | Leave the market resale queue | JWT |
| `GET` | `/market/queues` | List every resale queue the caller waits in | JWT |
| `GET` | `/market/assignments` | List the caller's recent market assignments | JWT |
| `GET` | `/market/assignments/pending` | Get the caller's assignment still awaiting payment | JWT |
| `GET` | `/market/assignments/{assignment_id}` | Get a specific market assignment | JWT |
| `PUT` | `/market/assignments/{assignment_id}/holders` | Set holder name and identity document for the incoming ticket | JWT |
| `POST` | `/market/assignments/{assignment_id}/decline` | Decline a market assignment | JWT |
| `POST` | `/billing/market-assignments/{assignment_id}/charge` | Charge the market assignment | JWT |

Full spec: [`packages/contracts/openapi/sales/openapi.yaml`](../../../../../../packages/contracts/openapi/sales/openapi.yaml)

## Events

### Published

| Event | NATS Subject | Description |
|-------|-------------|-------------|
| `ReservationCreated` | `sales.reservation.created.v1` | Emitted when a reservation was successfully created and inventory locked. |
| `ReservationExpired` | `sales.reservation.expired.v1` | Emitted when a reservation TTL elapsed without payment. |
| `ReservationCancelled` | `sales.reservation.cancelled.v1` | Emitted when a reservation was explicitly cancelled. |
| `ReservationPaid` | `sales.reservation.paid.v1` | Emitted when a reservation was settled after successful payment. |
| `MarketTicketFreeze` | `market.ticket.freeze.v1` | Emitted when a ticket was listed for resale, so Ticketing stops it being usable at the door. |
| `MarketTransfer` | `market.transfer.v1` | Emitted when a listed ticket changed owner, carrying the new holder's name and identity document. |
| `MarketListingExpired` | `market.listing.expired.v1` | Emitted when a listing expired without a buyer and the ticket returns to its holder. |
| `MarketAssignmentCreated` | `market.assignment.created.v1` | Emitted when a listing was offered to the next buyer in the resale queue. No service subscribes to it yet. |

The four `market.*` subjects belong to the resale marketplace, which lives in this service but publishes under its own prefix and therefore its own stream. Sales also publishes audit records to `audit.events.v1`.

Schemas: [`packages/contracts/openapi/sales/events/`](../../../../../../packages/contracts/openapi/sales/events/)

Every event is recorded in the `sales.event_outbox` table inside the same transaction as the change that caused it, and the `outbox_drainer` job publishes it afterwards. The request never talks to the broker.

### Consumed

| Event | NATS Subject | Action |
|-------|-------------|--------|
| `EventPublished` | `catalog.event.published.v1` | Upserts the `EventContext` projection with capacity and dates. |
| `EventUpdated` | `catalog.event.updated.v1` | Refreshes the `EventContext` projection. |
| `EventCancelled` | `catalog.event.cancelled.v1` | Marks event context as cancelled and cancels open reservations. |
| `EventDraft` | `catalog.event.draft.v1` | Marks the event context as draft. No service publishes this subject, so the handler never fires. |
| `TicketTypeCreated` | `catalog.ticket_type.created.v1` | Upserts the `TicketTypeInventory` projection. |
| `TicketTypeUpdated` | `catalog.ticket_type.updated.v1` | Updates the inventory projection. |
| `UserRegistered` | `identity.user.registered.v1` | Upserts the `UserAgeContext` projection for fraud scoring, including `phone_e164` for VoIP carrier lookup. |
| `FingerprintSeen` | `identity.fingerprint.seen.v1` | Upserts the `FingerprintContext` projection for device reuse fraud signal. |
| `PaymentSucceeded` | `payments.payment.succeeded.v1` | Marks the linked reservation as paid via `SettlementService`. |
| `PaymentRefunded` | `payments.payment.refunded.v1` | Cancels the reservation on full refund. |
| `ChargebackOpened` | `payments.chargeback.opened.v1` | Cancels the reservation on chargeback. |

## Background Workers

| Worker | Type | Description |
|--------|------|-------------|
| `reservation_expirer` | arq job, every minute | Sweeps expired reservations in batches and publishes `ReservationExpired`. |
| `queue_admitter` | arq job, every minute | Admits queued users when capacity becomes available. |
| `market_assigner` | arq job, every minute | Offers each open listing to the next buyer in the resale queue. |
| `market_expirer` | arq job, every minute | Expires unclaimed resale offers and returns the listing to the queue. |
| `outbox_drainer` | arq job, every minute | Publishes to NATS every domain event waiting in `sales.event_outbox`, retrying with backoff and parking a row after eight attempts. |
| `catalog.*` | NATS subscriber | Keeps the `EventContext` and `TicketTypeInventory` projections up to date. |
| `identity.*` | NATS subscriber | Keeps the `UserAgeContext` and `FingerprintContext` projections up to date. |
| `payments.*` | NATS subscriber | Handles payment settlement and reservation cancellation. |

The arq jobs run in the `sales-arq-worker` container, which consumes the `qrew:jobs:sales` queue. The NATS subscribers run in the separate `sales-worker` container.

## Internal Dependencies

| Package | Purpose |
|---------|---------|
| `contracts` | Domain event schemas |
| `exceptions` | Shared HTTP exception types |
| `idempotency` | Redis backed idempotency keys |
| `locking` | Redis distributed locks for inventory |
| `messaging` | NATS JetStream publisher and subscriber |
| `middleware` | Request ID, correlation, and security headers |
| `observability` | OpenTelemetry setup |
| `outbox` | Transactional outbox mixin, recorder, and drainer |
| `worker` | arq worker bootstrap |

## External Dependencies

| Service | Purpose |
|---------|---------|
| PostgreSQL | Reservations, queue, and projection store |
| Redis | Distributed inventory locks, idempotency keys, and rate limiting |
| NATS JetStream | Domain event publishing and consumption |

## Key Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection string. |
| `REDIS_URL` | Redis connection URL. |
| `NATS_URL` | NATS server address. |
| `INTERNAL_API_KEY` | Shared secret for internal service to service calls. |
| `ACCESS_JWT_PRIVATE_KEY` | EC private key for user JWT verification. |
| `QUEUE_JWT_PRIVATE_KEY` | EC private key for queue admission tokens. |
| `PAYMENTS_DEFAULT_CURRENCY` | Default currency for new reservations. Defaults to `EUR`. |
| `RESERVATION_TTL_SECONDS` | Seconds before an unpaid reservation expires. Defaults to 600. |
| `RESERVATION_SWEEP_BATCH_SIZE` | Number of reservations processed per expiry sweep. Defaults to 100. |
| `QUEUE_JOIN_LEAD_SECONDS` | Seconds before an event that a user can join the queue. Defaults to 300. |
| `QUEUE_REDEEM_WINDOW_SECONDS` | Time window in seconds to redeem a queue admission. Defaults to 120. |
| `FRAUD_SIGNALS_ENABLED` | Flag to enable fraud scoring on reservations. Defaults to true. |
| `FRAUD_SCORE_BLOCK_THRESHOLD` | Score above which a reservation is auto-blocked. Defaults to 80. |
| `FRAUD_SCORE_REVIEW_THRESHOLD` | Score above which a reservation is flagged for review. Defaults to 40. |
| `FRAUD_WEIGHT_VOIP_PHONE` | Fraud score added when the user's phone is detected as VoIP. Defaults to 60. |
| `TWILIO_ACCOUNT_SID` | Twilio account SID for phone carrier lookup. Optional. VoIP signal is skipped if unset. |
| `TWILIO_AUTH_TOKEN` | Twilio auth token for phone carrier lookup. |
| `TRUSTED_PROXY_IP` | Trusted reverse proxy IP for real client IP extraction. |
| `IDEMPOTENCY_ENABLED` | Flag to enable idempotency key enforcement. Defaults to true. |
| `RATELIMIT_ENABLED` | Flag to enable API rate limiting. Defaults to true. |
| `OTEL_ENABLED` | Flag to enable OpenTelemetry tracing. |
| `OTEL_ENDPOINT` | OTLP gRPC endpoint. Defaults to `http://localhost:4317`. |
