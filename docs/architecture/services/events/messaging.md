# Event System

Qrew uses NATS JetStream for asynchronous cross-service communication.

All domain events are wrapped in a standard `EventEnvelope` and published to named JetStream streams. Each consuming service maintains its own durable consumer and local projections.

No service queries another service's database.

## EventEnvelope

Every message published to a JetStream stream uses this envelope:

```json
{
  "event_id": "uuid",
  "occurred_at": "2026-01-01T12:00:00Z",
  "aggregate_type": "user",
  "aggregate_id": "uuid",
  "actor_id": "uuid | null",
  "data": { },
  "_otel": {
    "traceparent": "string | null",
    "tracestate": "string | null"
  }
}
```

* `event_id`: globally unique, used for idempotency deduplication at the consumer
* `occurred_at`: wall clock time at the publisher
* `aggregate_type` / `aggregate_id`: identify the domain object the event belongs to
* `actor_id`: the user or system that triggered the action, if applicable
* `data`: event-specific payload, typed per contract

## Delivery guarantees

* JetStream provides at-least-once delivery. Every consumer must be idempotent.
* All consumers use `DeliverPolicy.ALL` so they replay from the beginning on first start.
* The Gateway fanout consumer uses `DeliverPolicy.NEW` and only delivers live messages.
* On handler failure a message is nack'd and redelivered by NATS after the ack wait window.
* Default ack wait: 30 seconds.

## Audit events

Every service publishes security and business audit records to `audit.events.v1` via the shared `auditor` package. The Audit service subscribes and appends each record to a cryptographically chained log. No service reads the audit log directly.

## Naming convention

```
<service>.<aggregate>.<action>.v1
```

Examples: `identity.user.registered.v1`, `payments.payment.succeeded.v1`

Exceptions:
* `audit.events.v1`: single subject for all audit records, from all services
* `ws.fanout.v1`: internal subject used by Identity to push real-time notifications to Gateway
* `ticketing.ticket.state_changed`: internal subject without `.v1` suffix (legacy)
