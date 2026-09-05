# Messaging System

Qrew uses NATS JetStream for asynchronous cross-service communication.

All domain events are wrapped in a standard `EventEnvelope` and published to named JetStream streams. Each consuming service maintains its own durable consumer and local projections.

A publisher never hands the envelope to the broker while serving a request. It records the event in its own `event_outbox` table inside the transaction that changed the state, and a drainer job builds the envelope and publishes it a moment later. See [streams.md](streams.md) for the retry and dead letter semantics.

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
* `aggregate_type` and `aggregate_id`: identify the domain object the event belongs to
* `actor_id`: the user or system that triggered the action, if applicable
* `data`: event-specific payload, typed per contract
* `_otel`: the trace context captured when the outbox row was written, so a consumer continues the trace that produced the event instead of starting its own

## Delivery guarantees

* JetStream delivers at least once. Every consumer must be idempotent.
* All consumers use `DeliverPolicy.ALL` so they replay from the beginning on first start.
* The Gateway fanout consumer uses `DeliverPolicy.NEW` and only delivers live messages.
* On handler failure a message is nack'd and redelivered by NATS after the ack wait window.
* No consumer sets `ack_wait`, so the JetStream server default of 30 seconds applies.

## Audit events

Identity, Catalog, Sales, Ticketing and Entry publish security and business audit records to `audit.events.v1`, each through its own `services/application/audit.py`. Payments and the Gateway publish none. The Audit service subscribes and appends each record to a cryptographically chained log.

Audit records bypass the outbox on purpose. A lost record costs an entry in the trail and nothing else, whereas routing them through the outbox would put every write on the drainer's minute-long cycle. Identity reads the trail back over HTTP rather than from the broker.

## Naming convention

```
<service>.<aggregate>.<action>.v1
```

Examples: `identity.user.registered.v1`, `payments.payment.succeeded.v1`

Exceptions:
* `audit.events.v1`: single subject for all audit records, from the five services that write them
* `ws.fanout.v1`: internal subject Identity and Entry use to push live notifications to the Gateway
* `ticketing.ticket.state_changed` and `ticketing.ticket.restored`: the two ticketing subjects carry no `.v1` suffix
* `market.*`: the resale marketplace lives inside Sales but publishes under its own prefix, and therefore into its own stream
