# Payments

> Payment service for Stripe integration and payment lifecycle management.

## Overview

Payments is the Stripe integration service in the platform. It creates and tracks PaymentIntents, handles Stripe webhook callbacks for payment outcomes, and publishes payment state transitions as domain events. It does not manage reservations, inventory, or ticket issuance.

## Responsibilities

1. Creates and tracks Stripe PaymentIntents with 3DS2 enforcement via `request_three_d_secure: any`.
2. Receives and verifies Stripe webhook callbacks.
3. Publishes payment outcome events to the platform.
4. Encrypts PII associated with payments at rest.
5. Does not manage reservations, inventory, or ticket issuance.

## HTTP API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/reservations/{id}/payment` | Initiate a payment for a reservation | JWT |
| `POST` | `/market-assignments/{id}/payment` | Initiate a payment for a market assignment | JWT |
| `POST` | `/payments/webhook` | Receive a Stripe webhook for payment outcomes | Stripe signature |

Full spec: [`packages/contracts/openapi/payments/openapi.yaml`](../../../../../../packages/contracts/openapi/payments/openapi.yaml)

## Events

### Published

| Event | NATS Subject | Description |
|-------|-------------|-------------|
| `PaymentInitiated` | `payments.payment.initiated.v1` | Emitted when a PaymentIntent was created with Stripe. No service subscribes to it yet. |
| `PaymentSucceeded` | `payments.payment.succeeded.v1` | Emitted when Stripe confirmed the payment was captured. |
| `PaymentFailed` | `payments.payment.failed.v1` | Emitted when Stripe reported the payment as failed. |
| `PaymentRefunded` | `payments.payment.refunded.v1` | Emitted when a full or partial refund was processed. |
| `ChargebackOpened` | `payments.chargeback.opened.v1` | Emitted when a chargeback dispute was opened by the card issuer. |
| `ChargebackClosed` | `payments.chargeback.closed.v1` | Emitted when the card issuer resolved the dispute. |

Payments is the one service that publishes no audit records to `audit.events.v1`.

Schemas: [`packages/contracts/openapi/payments/events/`](../../../../../../packages/contracts/openapi/payments/events/)

Every event is recorded in the `payments.event_outbox` table inside the same transaction as the change that caused it, and the `outbox_drainer` job publishes it afterwards. The request never talks to the broker.

### Consumed

This service does not consume events from other services.

## Background Workers

| Worker | Type | Description |
|--------|------|-------------|
| `outbox_drainer` | arq job, every minute | Publishes to NATS every domain event waiting in `payments.event_outbox`, retrying with backoff and parking a row after eight attempts. |

This job runs in the `payments-worker` container, an arq runner on the `qrew:jobs:payments` queue. It does not subscribe to NATS; it only publishes what the drainer takes from the outbox. Everything else is driven by incoming HTTP requests.

## Internal Dependencies

| Package | Purpose |
|---------|---------|
| `exceptions` | Shared HTTP exception types |
| `idempotency` | Redis backed idempotency keys |
| `messaging` | NATS JetStream publisher |
| `middleware` | Request ID, correlation, and security headers |
| `observability` | OpenTelemetry setup |
| `outbox` | Transactional outbox mixin, recorder, and drainer |

## External Dependencies

| Service | Purpose |
|---------|---------|
| PostgreSQL | Payment record and audit store |
| Redis | Idempotency keys and rate limiting |
| NATS JetStream | Domain event publishing |
| Stripe | Payment processing and webhook delivery |
| Sales service | HTTP settlement notification |

## Key Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection string. |
| `REDIS_URL` | Redis connection URL. |
| `NATS_URL` | NATS server address. |
| `INTERNAL_API_KEY` | Shared secret for internal service to service calls. |
| `SALES_URL` | Base URL of the sales service. Defaults to `http://localhost:8003`. |
| `ACCESS_JWT_PRIVATE_KEY` | EC private key for JWT verification. |
| `ACCESS_JWT_PREVIOUS_PUBLIC_KEYS` | Comma separated previous public keys for key rotation. |
| `PII_ENCRYPTION_KEY` | AES key for PII field encryption at rest. |
| `PII_ENCRYPTION_PREVIOUS_KEYS` | Previous PII keys for decryption during key rotation. |
| `STRIPE_SECRET_KEY` | Stripe secret API key. |
| `STRIPE_WEBHOOK_SIGNING_SECRET` | Stripe webhook endpoint signing secret. |
| `STRIPE_API_VERSION` | Pinned Stripe API version. Defaults to `2024-06-20`. |
| `PAYMENTS_WEBHOOK_IDEMPOTENCY_TTL_SECONDS` | TTL in seconds for webhook idempotency keys. Defaults to 86400. |
| `IDEMPOTENCY_ENABLED` | Flag to enable idempotency key enforcement. Defaults to true. |
| `RATELIMIT_ENABLED` | Flag to enable API rate limiting. Defaults to true. |
| `OTEL_ENABLED` | Flag to enable OpenTelemetry tracing. |
| `OTEL_ENDPOINT` | OTLP gRPC endpoint. Defaults to `http://localhost:4317`. |
