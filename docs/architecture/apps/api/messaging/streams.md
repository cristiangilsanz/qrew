# Streams Configuration

## Streams

| Stream | Wildcard subjects | Retention | Created by | Description |
|---|---|---|---|---|
| `IDENTITY` | `identity.>` | Limits (default) | Sales, Ticketing | Identity domain events |
| `CATALOG` | `catalog.>` | Limits (default) | Identity, Sales, Ticketing, Entry | Catalog domain events |
| `SALES` | `sales.>` | Limits (default) | Ticketing | Sales and reservation events |
| `MARKET` | `market.>` | Limits (default) | Ticketing | Resale marketplace events |
| `PAYMENTS` | `payments.>` | Limits (default) | Identity, Sales | Payment lifecycle events |
| `ticketing` | `ticketing.>` | Limits (default) | Entry | Ticket state transitions |
| `AUDIT` | `audit.>` | Limits (default) | Audit | Cross-service audit records |
| `GATEWAY` | `ws.>` | Limits (default) | Gateway | WebSocket fanout notifications |

Nothing provisions the streams ahead of time. Each subscriber calls `find_stream_name_by_subject` on startup and creates the stream itself when the lookup fails, so whichever consumer starts first is the one that creates it.

That makes the stream **name** a shared constant across every service that touches the same wildcard, and getting it wrong is a silent failure rather than an error: the subject lookup succeeds against the stream a different service already created, and the subsequent `subscribe` then fails with `stream not found` because the name does not match. Every consumer of `catalog.>` must therefore agree on `CATALOG`, and so on.

The `ticketing` stream is lowercase, unlike all the others, because the single subscriber that creates it spells it that way.

## Consumers

All consumers are durable push consumers unless noted otherwise.

### Shared pattern

Each worker subscribes with:

```python
ConsumerConfig(
    durable_name=durable,
    deliver_policy=DeliverPolicy.ALL,
    filter_subject=subject,
)
```

`DeliverPolicy.ALL` means consumers replay from the start of the stream on first connection, which supports projection bootstrapping after a service is deployed fresh. No consumer overrides `ack_wait`, so the server default applies.

The entry subscribers are the exception: they call `js.subscribe` with a callback and a durable name but no `ConsumerConfig`, so they take the client defaults.

### Consumer registry

| Durable name | Stream | Subject(s) | Consumer service |
|---|---|---|---|
| `sales-identity-handler-*` | `IDENTITY` | `identity.user.registered.v1`, `identity.fingerprint.seen.v1` | Sales |
| `ticketing-identity-handler-*` | `IDENTITY` | `identity.device.attested.v1`, `identity.device.revoked.v1` | Ticketing |
| `identity-catalog-handler-*` | `CATALOG` | `catalog.event.cancelled.v1` | Identity |
| `sales-catalog-handler-*` | `CATALOG` | `catalog.event.published.v1`, `catalog.event.updated.v1`, `catalog.event.cancelled.v1`, `catalog.event.draft.v1`, `catalog.ticket_type.created.v1`, `catalog.ticket_type.updated.v1` | Sales |
| `ticketing-catalog-handler-*` | `CATALOG` | `catalog.event.published.v1`, `catalog.event.ongoing.v1`, `catalog.event.cancelled.v1`, `catalog.event.draft.v1` | Ticketing |
| `ticketing-sales-handler-*` | `SALES` | `sales.reservation.created.v1`, `sales.reservation.paid.v1`, `sales.reservation.cancelled.v1`, `sales.reservation.expired.v1` | Ticketing |
| `ticketing-market-handler-*` | `MARKET` | `market.ticket.freeze.v1`, `market.transfer.v1`, `market.listing.expired.v1` | Ticketing |
| `identity-payment-handler-*` | `PAYMENTS` | `payments.payment.succeeded.v1`, `payments.payment.failed.v1`, `payments.payment.refunded.v1`, `payments.chargeback.opened.v1`, `payments.chargeback.closed.v1` | Identity |
| `sales-payment-handler-*` | `PAYMENTS` | `payments.payment.succeeded.v1`, `payments.payment.refunded.v1`, `payments.chargeback.opened.v1` | Sales |
| `audit-events-handler` | `AUDIT` | `audit.events.v1` | Audit |
| `gateway-fanout-handler` | `GATEWAY` | `ws.fanout.v1` | Gateway |
| `entry-projector` | `ticketing` | `ticketing.ticket.state_changed` | Entry |
| `entry-catalog-catalog-event-published-v1` | `CATALOG` | `catalog.event.published.v1` | Entry |
| `entry-catalog-catalog-event-updated-v1` | `CATALOG` | `catalog.event.updated.v1` | Entry |
| `entry-catalog-catalog-event-ongoing-v1` | `CATALOG` | `catalog.event.ongoing.v1` | Entry |
| `entry-catalog-membership` | `CATALOG` | `catalog.membership.changed.v1` | Entry |

Durable names suffixed with `*` are per subject.

### Gateway exception

The Gateway fanout consumer uses `DeliverPolicy.NEW` instead of `DeliverPolicy.ALL`. 

It only forwards live messages. Historical replay would flood open WebSocket connections with stale notifications.

## Outbox

Catalog, sales, payments, ticketing and identity all use a transactional outbox instead of publishing directly from request handlers. Domain events are written atomically to an `event_outbox` table in the same transaction as the business write. A drainer job polls that table every minute and publishes to JetStream, marking rows as dispatched. A row that the broker refuses is retried with a growing backoff of 5, 15, 60, 300, 900, 1800 and 3600 seconds, and after 8 attempts it is parked with `dlq_reason = 'attempts_exhausted'` rather than retried for ever.

The table, the recorder and the drainer live in the shared `outbox` package, so the five services share the same columns and the same semantics. Identity keeps a second, unrelated `outbox` table that defers arq jobs rather than domain events.

| Service | Table | Drainer job | Container |
|---|---|---|---|
| Catalog | `catalog.event_outbox` | `catalog.outbox.drain` | `catalog-worker` |
| Sales | `sales.event_outbox` | `sales.outbox.drain` | `sales-arq-worker` |
| Payments | `payments.event_outbox` | `payments.outbox.drain` | `payments-worker` |
| Ticketing | `ticketing.event_outbox` | `ticketing.outbox.drain` | `ticketing-arq-worker` |
| Identity | `identity.event_outbox` | `identity.event_outbox.drain` | `identity-arq-worker` |

This guarantees that events are never lost even if the NATS connection is unavailable at the time of the business operation.
