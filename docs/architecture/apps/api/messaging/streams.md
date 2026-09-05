# Streams Configuration

## Streams

| Stream | Wildcard subjects | Retention | Description |
|---|---|---|---|
| `IDENTITY` | `identity.>` | Limits (default) | Identity domain events |
| `CATALOG` | `catalog.>` | Limits (default) | Catalog domain events |
| `SALES` | `sales.>` | Limits (default) | Sales and reservation events |
| `PAYMENTS` | `payments.>` | Limits (default) | Payment lifecycle events |
| `AUDIT` | `audit.>` | Limits (default) | Cross-service audit records |
| `GATEWAY` | `ws.fanout.v1` | Limits (default) | WebSocket fanout notifications |

Streams are provisioned in infrastructure.

Each service verifies its required stream exists at startup and logs a warning or raises a runtime error if not found.

## Consumers

All consumers are durable push consumers unless noted otherwise.

### Shared pattern

Each worker subscribes with:

```python
ConsumerConfig(
    durable_name=DURABLE,
    deliver_policy=DeliverPolicy.ALL,
    ack_wait=30,
    filter_subject=subject,
)
```

`DeliverPolicy.ALL` means consumers replay from the start of the stream on first connection, which supports projection bootstrapping after a service is deployed fresh.

### Consumer registry

| Durable name | Stream | Subject(s) | Consumer service |
|---|---|---|---|
| `sales-identity-handler-*` | `IDENTITY` | `identity.user.registered.v1`, `identity.fingerprint.seen.v1` | Sales |
| `ticketing-identity-handler-*` | `IDENTITY` | `identity.device.attested.v1`, `identity.device.revoked.v1` | Ticketing |
| `identity-catalog-handler-*` | `CATALOG` | `catalog.event.cancelled.v1` | Identity |
| `sales-catalog-handler-*` | `CATALOG` | `catalog.event.*.v1`, `catalog.ticket_type.*.v1` | Sales |
| `ticketing-catalog-handler-*` | `CATALOG` | `catalog.event.*.v1`, `catalog.venue.created.v1` | Ticketing |
| `ticketing-sales-handler-*` | `SALES` | `sales.reservation.*.v1` | Ticketing |
| `identity-payment-handler-*` | `PAYMENTS` | `payments.payment.*.v1`, `payments.chargeback.*.v1` | Identity |
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
