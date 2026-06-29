# JetStream Configuration

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
| `entry-projector` | n/a | `ticketing.ticket.state_changed` | Entry |

Durable names suffixed with `*` are per-subject.

### Gateway exception

The Gateway fanout consumer uses `DeliverPolicy.NEW` instead of `DeliverPolicy.ALL`. 

It only forwards live messages. Historical replay would flood open WebSocket connections with stale notifications.

## Outbox (Identity only)

Identity uses a transactional outbox instead of publishing directly from request handlers. Domain events are written atomically to the `outbox` table in the same transaction as the business write. The outbox worker polls and publishes to JetStream, marking rows as dispatched. Failed rows enter a DLQ after a configurable retry count.

This guarantees that events are never lost even if the NATS connection is unavailable at the time of the business operation.
