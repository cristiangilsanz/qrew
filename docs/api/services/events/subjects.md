# Subject Registry

Full list of NATS subjects across all streams. See [jetstream.md](jetstream.md) for stream configuration.

## IDENTITY stream

Wildcard: `identity.>`

| Subject | Published by | Consumed by | Description |
|---|---|---|---|
| `identity.user.registered.v1` | Identity | Sales | New user account created |
| `identity.fingerprint.seen.v1` | Identity | Sales | Device fingerprint observed at login |
| `identity.device.attested.v1` | Identity | Ticketing | Device passed hardware attestation |
| `identity.device.revoked.v1` | Identity | Ticketing | Device revoked by user or admin |

## CATALOG stream

Wildcard: `catalog.>`

| Subject | Published by | Consumed by | Description |
|---|---|---|---|
| `catalog.event.published.v1` | Catalog | Sales, Ticketing | Event moved to published state |
| `catalog.event.cancelled.v1` | Catalog | Identity, Sales, Ticketing | Event cancelled |
| `catalog.event.draft.v1` | Catalog | Sales, Ticketing | Event moved back to draft |
| `catalog.venue.created.v1` | Catalog | Ticketing | New venue created |
| `catalog.ticket_type.created.v1` | Catalog | Sales | New ticket type added to an event |
| `catalog.ticket_type.updated.v1` | Catalog | Sales | Ticket type capacity or price changed |

## SALES stream

Wildcard: `sales.>`

| Subject | Published by | Consumed by | Description |
|---|---|---|---|
| `sales.reservation.created.v1` | Sales | Ticketing | New reservation placed |
| `sales.reservation.paid.v1` | Sales | Ticketing | Reservation confirmed after payment |
| `sales.reservation.cancelled.v1` | Sales | Ticketing | Reservation cancelled or expired |

## PAYMENTS stream

Wildcard: `payments.>`

| Subject | Published by | Consumed by | Description |
|---|---|---|---|
| `payments.payment.initiated.v1` | Payments | — | Payment intent created with Stripe |
| `payments.payment.succeeded.v1` | Payments | Identity, Sales | Payment confirmed by Stripe webhook |
| `payments.payment.failed.v1` | Payments | Identity | Payment failed |
| `payments.payment.refunded.v1` | Payments | Identity, Sales | Payment refunded |
| `payments.chargeback.opened.v1` | Payments | Identity, Sales | Chargeback dispute opened |
| `payments.chargeback.closed.v1` | Payments | Identity | Chargeback dispute closed |

## TICKETING (no dedicated stream)

| Subject | Published by | Consumed by | Description |
|---|---|---|---|
| `ticketing.ticket.state_changed` | Ticketing | Entry | Ticket state transition occurred |
| `ticketing.ticket.restored` | Ticketing | — | Ticket restored after device re-enrolment |

## AUDIT stream

Wildcard: `audit.>`

| Subject | Published by | Consumed by | Description |
|---|---|---|---|
| `audit.events.v1` | All services | Audit | Security and business audit record |

## GATEWAY stream

| Subject | Published by | Consumed by | Description |
|---|---|---|---|
| `ws.fanout.v1` | Identity | Gateway | Real-time notification to be forwarded over WebSocket |
