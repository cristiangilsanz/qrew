# Payments Database Schema

```mermaid
erDiagram
    payments {
        UUID id PK
        UUID reservation_id "nullable, unique"
        UUID market_assignment_id "nullable, unique"
        UUID user_id "nullable"
        string provider "default: stripe"
        string provider_payment_intent_id "nullable, indexed"
        int amount_cents "check: >= 0"
        string currency
        string status "default: requires_action"
        bytes client_secret_ciphertext "nullable"
        string failure_code "nullable"
        text failure_message "nullable"
        timestamp created_at "default: now()"
        timestamp updated_at "default: now()"
    }

    event_outbox["event_outbox (transactional outbox)"] {
        UUID id PK
        string subject
        string aggregate_type
        string aggregate_id
        string actor_id
        jsonb payload
        timestamp created_at
        timestamp dispatched_at
        int attempt_count
        text last_error
        timestamp next_attempt_at
        string dlq_reason
    }
```

## Schema: `payments`

### Table: `payments`

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | `UUID` | NOT NULL | — | Primary key |
| `reservation_id` | `UUID` | NULL | — | Unique; mutually exclusive with `market_assignment_id` |
| `market_assignment_id` | `UUID` | NULL | — | Unique; mutually exclusive with `reservation_id` |
| `user_id` | `UUID` | NULL | — | |
| `provider` | `VARCHAR(32)` | NOT NULL | `'stripe'` | Payment provider name |
| `provider_payment_intent_id` | `VARCHAR(255)` | NULL | — | Provider-side intent ID |
| `amount_cents` | `INTEGER` | NOT NULL | — | Amount in minor currency units |
| `currency` | `VARCHAR(3)` | NOT NULL | — | ISO 4217 currency code |
| `status` | `VARCHAR(20)` | NOT NULL | `'requires_action'` | Payment status |
| `client_secret_ciphertext` | `BYTEA` | NULL | — | Encrypted Stripe client secret |
| `failure_code` | `VARCHAR(64)` | NULL | — | Provider failure code |
| `failure_message` | `TEXT` | NULL | — | Provider failure message |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | |

### Constraints

| Name | Type | Definition |
|---|---|---|
| `payments_pkey` | PRIMARY KEY | `id` |
| `uq_payments_reservation_id` | UNIQUE | `reservation_id` |
| `uq_payments_market_assignment_id` | UNIQUE | `market_assignment_id` |
| `ck_payments_amount` | CHECK | `amount_cents >= 0` |
| `ck_payments_context` | CHECK | `num_nonnulls(reservation_id, market_assignment_id) = 1` |

### Indexes

| Name | Columns |
|---|---|
| `ix_payments_provider_payment_intent_id` | `provider_payment_intent_id` |
| `ix_payments_market_assignment_id` | `market_assignment_id` |

### Table: `event_outbox`

Holds every domain event the service records inside the transaction that caused it. The `outbox_drainer` job publishes each pending row to NATS and stamps `dispatched_at`, so no event is lost when the request path cannot reach the broker. The table and the drainer come from the shared `outbox` package.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | `UUID` | NOT NULL | `gen_random_uuid()` | Primary key |
| `subject` | `VARCHAR(128)` | NOT NULL | — | NATS subject the row is published to |
| `aggregate_type` | `VARCHAR(64)` | NOT NULL | — | Always `payment` |
| `aggregate_id` | `VARCHAR(64)` | NOT NULL | — | Payment ID |
| `actor_id` | `VARCHAR(64)` | NULL | — | User the change is attributed to |
| `payload` | `JSONB` | NOT NULL | — | Event body, becomes `data` in the envelope |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | Becomes `occurred_at` in the envelope |
| `dispatched_at` | `TIMESTAMPTZ` | NULL | — | NULL while the row is still pending |
| `attempt_count` | `INTEGER` | NOT NULL | `0` | Parked at 8 attempts |
| `last_error` | `TEXT` | NULL | — | Repr of the last publish failure |
| `next_attempt_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | Backoff of 5, 15, 60, 300, 900, 1800, 3600 seconds |
| `dlq_reason` | `VARCHAR(64)` | NULL | — | `attempts_exhausted` once the row is parked |

### Indexes

| Name | Columns |
|---|---|
| `ix_payments_event_outbox_pending` | `next_attempt_at`, partial `WHERE dispatched_at IS NULL AND dlq_reason IS NULL` |
