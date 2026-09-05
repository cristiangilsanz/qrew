# Catalog Database Schema

```mermaid
erDiagram
    organisations {
        UUID id PK
        VARCHAR_64 slug UK
        VARCHAR_128 name
        TEXT description
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        TIMESTAMPTZ deleted_at
    }

    organisation_members {
        UUID organisation_id PK,FK
        UUID user_id PK
        organisation_role role
        TIMESTAMPTZ joined_at
    }

    venues {
        UUID id PK
        VARCHAR_128 name
        VARCHAR_256 address_line
        VARCHAR_96 city
        CHAR_2 country
        NUMERIC_9_6 latitude
        NUMERIC_9_6 longitude
        INTEGER geofence_radius_m
        VARCHAR_64 timezone
        TEXT description
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        TIMESTAMPTZ deleted_at
    }

    events {
        UUID id PK
        UUID organisation_id FK
        UUID venue_id FK
        VARCHAR_160 name
        TEXT description
        VARCHAR_500 image_url
        VARCHAR_16 status
        VARCHAR_128 organiser_name
        VARCHAR_96 venue_city
        TIMESTAMPTZ starts_at
        TIMESTAMPTZ ends_at
        TIMESTAMPTZ sale_starts_at
        TIMESTAMPTZ sale_ends_at
        INTEGER max_tickets_per_user
        BOOLEAN queue_required
        INTEGER queue_admit_rate_per_minute
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        TIMESTAMPTZ published_at
        TIMESTAMPTZ started_at
        TIMESTAMPTZ cancelled_at
        TSVECTOR search_vector
    }

    ticket_types {
        UUID id PK
        UUID event_id FK
        VARCHAR_32 name
        TEXT description
        INTEGER capacity
        INTEGER reserved_count
        INTEGER price_cents
        CHAR_3 currency
        INTEGER position
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        TIMESTAMPTZ deleted_at
    }

    event_outbox["event_outbox (transactional outbox)"] {
        UUID id PK
        VARCHAR_128 subject
        VARCHAR_64 aggregate_type
        VARCHAR_64 aggregate_id
        VARCHAR_64 actor_id
        JSONB payload
        TIMESTAMPTZ created_at
        TIMESTAMPTZ dispatched_at
        INTEGER attempt_count
        TEXT last_error
        TIMESTAMPTZ next_attempt_at
        VARCHAR_64 dlq_reason
    }

    organisations ||--o{ organisation_members : "has"
    organisations ||--o{ events : "owns"
    venues ||--o{ events : "hosts"
    events ||--o{ ticket_types : "has"
```

## Enum Types

| Type | Values |
|---|---|
| `organisation_role` | `member`, `manager`, `owner` |

## Indexes

| Table | Index Name | Columns | Type |
|---|---|---|---|
| `organisations` | `uq_organisations_slug` | `slug` | UNIQUE |
| `venues` | `ix_venues_city_country` | `city, country` | BTREE |
| `events` | `ix_events_organisation_id` | `organisation_id` | BTREE |
| `events` | `ix_events_venue_id` | `venue_id` | BTREE |
| `events` | `ix_events_status_starts_at` | `status, starts_at` | BTREE |
| `events` | `ix_events_search_vector` | `search_vector` | GIN |
| `ticket_types` | `ix_ticket_types_event_id` | `event_id` | BTREE |
| `event_outbox` | `ix_catalog_event_outbox_pending` | `next_attempt_at` | BTREE, partial `WHERE dispatched_at IS NULL AND dlq_reason IS NULL` |

## Check Constraints

| Table | Constraint Name | Expression |
|---|---|---|
| `events` | `ck_events_time_window` | `starts_at < ends_at` |
| `events` | `ck_events_sale_window` | `sale_starts_at < sale_ends_at` |
| `events` | `ck_events_sale_before_start` | `sale_ends_at <= starts_at` |
| `events` | `ck_events_max_tickets` | `max_tickets_per_user >= 1 AND max_tickets_per_user <= 20` |
| `events` | `ck_events_queue_admit_rate` | `queue_admit_rate_per_minute >= 1 AND queue_admit_rate_per_minute <= 600` |
| `ticket_types` | `uq_ticket_types_event_name` | UNIQUE `(event_id, name)` |
| `ticket_types` | `ck_ticket_types_capacity` | `capacity >= 1 AND capacity <= 100000` |
| `ticket_types` | `ck_ticket_types_reserved` | `reserved_count >= 0 AND reserved_count <= capacity` |
| `ticket_types` | `ck_ticket_types_price` | `price_cents >= 0 AND price_cents <= 10000000` |

## Transactional Outbox

`catalog.event_outbox` holds every domain event the service records inside the transaction that caused it. The `outbox_drainer` job publishes each pending row to NATS and stamps `dispatched_at`. A row that fails is retried with a growing backoff of 5, 15, 60, 300, 900, 1800 and 3600 seconds, and after 8 attempts it is parked with `dlq_reason = 'attempts_exhausted'` instead of retried for ever.

The table and the drainer come from the shared `outbox` package, so catalog, sales, payments, ticketing and identity all use the same columns and the same semantics.
