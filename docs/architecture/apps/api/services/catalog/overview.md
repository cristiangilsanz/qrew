# Catalog

> Catalog service for event publication and ticket type management.

## Overview

Catalog is the source of truth for the public event catalog in the platform. It manages organisation and venue creation, event publication and editing, ticket type definition, and public event search and discovery. It does not manage reservations, ticket issuance, or payment.

## Responsibilities

1. Manages organisation creation and member management.
2. Creates venues and associates them with organisations.
3. Handles event creation, editing, and publication.
4. Defines ticket types with name, price, capacity, and currency.
5. Provides event search and discovery, matching a query as a contiguous run of characters in the title or description and ranking the results by full-text relevance.
6. Does not manage reservations, ticket issuance, or payment.

## HTTP API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/organisations` | Create an organisation | JWT (admin only) |
| `GET` | `/organisations` | List organisations the caller belongs to | JWT |
| `GET` | `/organisations/search` | Search organisations by name or slug | JWT |
| `GET` | `/organisations/{id}` | Get public organisation profile | Public |
| `DELETE` | `/organisations/{id}` | Delete an organisation | JWT (owner) |
| `GET` | `/organisations/{id}/members` | List members of an organisation | JWT |
| `POST` | `/organisations/{id}/members` | Invite a member by email | JWT (manager) |
| `POST` | `/organisations/{id}/members/add` | Add a member by user ID | JWT (manager) |
| `DELETE` | `/organisations/{id}/members/{uid}` | Remove a member | JWT (manager) |
| `POST` | `/organisations/{id}/events` | Create a draft event | JWT (manager) |
| `GET` | `/organisations/{id}/events` | List events for an organisation | JWT (member) |
| `GET` | `/organisations/{id}/events/{eid}` | Get a single org event | JWT (member) |
| `POST` | `/venues` | Create a venue | JWT |
| `GET` | `/venues` | List all venues | JWT |
| `GET` | `/venues/{id}` | Get a venue by ID | JWT |
| `PATCH` | `/events/{id}` | Update event details (draft or published only) | JWT (manager) |
| `POST` | `/events/{id}/publish` | Publish a draft event | JWT (manager) |
| `POST` | `/events/{id}/start` | Mark a published event as ongoing | JWT (manager) |
| `POST` | `/events/{id}/cancel` | Cancel an event | JWT (manager) |
| `GET` | `/events` | Public catalog list with search and filters | Public |
| `GET` | `/events/search` | Search published events by title, organisation or venue | Public |
| `GET` | `/events/{id}` | Get a published event with ticket types | Public |
| `GET` | `/events/{id}/availability` | Lightweight availability check | Public |
| `POST` | `/events/{id}/ticket-types` | Add a ticket type (draft or published only) | JWT (manager) |
| `GET` | `/events/{id}/ticket-types` | List ticket types for an event | Public |
| `PATCH` | `/events/{id}/ticket-types/{tid}` | Update a ticket type (draft or published only) | JWT (manager) |
| `DELETE` | `/events/{id}/ticket-types/{tid}` | Delete a ticket type (draft or published only) | JWT (manager) |
| `GET` | `/_internal/events/{event_id}/members/{user_id}` | Report whether the event exists and the user belongs to its organisation | Internal |

An event reaches its ongoing state on its own, through the `event_lifecycle` job, so no screen calls `/events/{id}/start`. It stays available for an organiser who needs to force it.

Full spec: [`packages/contracts/openapi/catalog/openapi.yaml`](../../../../../../packages/contracts/openapi/catalog/openapi.yaml)

## Events

### Published

| Event | NATS Subject | Description |
|-------|-------------|-------------|
| `EventPublished` | `catalog.event.published.v1` | Emitted when an event was published and made visible. |
| `EventUpdated` | `catalog.event.updated.v1` | Emitted when event details are changed. |
| `EventOngoing` | `catalog.event.ongoing.v1` | Emitted when an event is marked as started. |
| `EventCancelled` | `catalog.event.cancelled.v1` | Emitted when a published event was cancelled. |
| `TicketTypeCreated` | `catalog.ticket_type.created.v1` | Emitted when a ticket type was added to an event. |
| `TicketTypeUpdated` | `catalog.ticket_type.updated.v1` | Emitted when a ticket type capacity or price changes. |
| `MembershipChanged` | `catalog.membership.changed.v1` | Emitted when an organisation roster changes, on creation, invitation, addition, or removal. A null `role` means the member left. |

Catalog also publishes audit records to `audit.events.v1`.

Schemas: [`packages/contracts/openapi/catalog/events/`](../../../../../../packages/contracts/openapi/catalog/events/)

Every event is recorded in the `catalog.event_outbox` table inside the same transaction as the change that caused it, and the `outbox_drainer` job publishes it afterwards. The request never talks to the broker.

### Consumed

This service does not consume events from other services.

## Background Workers

| Worker | Type | Description |
|--------|------|-------------|
| `search_reindexer` | arq job, daily at 05:00 | Rebuilds the full-text index that ranks the events a search returns. |
| `event_lifecycle` | arq job, every minute | Marks a published event as ongoing once its start time has passed, so nobody has to do it by hand. |
| `outbox_drainer` | arq job, every minute | Publishes to NATS every domain event waiting in `catalog.event_outbox`, retrying with backoff and parking a row after eight attempts. |

These jobs run in the `catalog-worker` container, an arq runner on the `qrew:jobs:catalog` queue. It does not subscribe to NATS; it only publishes what the drainer takes from the outbox.

## Internal Dependencies

| Package | Purpose |
|---------|---------|
| `contracts` | Domain event schemas |
| `db` | Async SQLAlchemy session factory |
| `exceptions` | Shared HTTP exception types |
| `idempotency` | Redis backed idempotency keys |
| `jobs` | arq job registration helpers |
| `locking` | Redis distributed locks |
| `messaging` | NATS JetStream publisher |
| `middleware` | Request ID, correlation, and security headers |
| `observability` | OpenTelemetry setup |
| `outbox` | Transactional outbox mixin, recorder, and drainer |

## External Dependencies

| Service | Purpose |
|---------|---------|
| PostgreSQL | Primary datastore |
| Redis | Idempotency keys and rate limiting |
| NATS JetStream | Domain event publishing |

## Key Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection string. |
| `REDIS_URL` | Redis connection URL. |
| `NATS_URL` | NATS server address. |
| `ACCESS_JWT_PRIVATE_KEY` | EC private key for JWT verification. |
| `ACCESS_JWT_PREVIOUS_PUBLIC_KEYS` | Comma separated previous public keys for key rotation. |
| `CORS_ORIGINS` | Allowed CORS origins. |
| `SEARCH_DEFAULT_LIMIT` | Default page size for search results. Defaults to 20. |
| `SEARCH_MAX_LIMIT` | Maximum page size for search results. Defaults to 100. |
| `IDEMPOTENCY_ENABLED` | Flag to enable idempotency key enforcement. Defaults to true. |
| `RATELIMIT_ENABLED` | Flag to enable API rate limiting. Defaults to true. |
| `OTEL_ENABLED` | Flag to enable OpenTelemetry tracing. |
| `OTEL_ENDPOINT` | OTLP gRPC endpoint. Defaults to `http://localhost:4317`. |
