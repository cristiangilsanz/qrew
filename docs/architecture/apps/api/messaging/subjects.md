# Subject Registry

Full list of NATS subjects across all streams. See [streams.md](streams.md) for stream configuration.

A blank **Consumed by** cell means the subject is published but nobody subscribes to it yet. A **Published by** cell reading `— (none)` means the opposite: a subscriber exists but no code emits the subject. Both are recorded rather than hidden, so the gap stays visible.

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
| `catalog.event.published.v1` | Catalog | Sales, Ticketing, Entry | Event moved to published state |
| `catalog.event.updated.v1` | Catalog | Sales, Entry | Event details changed |
| `catalog.event.ongoing.v1` | Catalog | Ticketing, Entry | Event started, whether by the lifecycle job or by an organiser |
| `catalog.event.cancelled.v1` | Catalog | Identity, Sales, Ticketing | Event cancelled |
| `catalog.event.draft.v1` | — (none) | Sales, Ticketing | Event moved back to draft. Sales and Ticketing both handle it, but no code publishes it, so the handlers never fire |
| `catalog.ticket_type.created.v1` | Catalog | Sales | New ticket type added to an event |
| `catalog.ticket_type.updated.v1` | Catalog | Sales | Ticket type capacity or price changed |
| `catalog.membership.changed.v1` | Catalog | Entry | Organisation roster changed. A null `role` means the member left |

## SALES stream

Wildcard: `sales.>`

| Subject | Published by | Consumed by | Description |
|---|---|---|---|
| `sales.reservation.created.v1` | Sales | Ticketing | New reservation placed |
| `sales.reservation.paid.v1` | Sales | Ticketing | Reservation confirmed after payment |
| `sales.reservation.cancelled.v1` | Sales | Ticketing | Reservation cancelled by the buyer or by an organiser |
| `sales.reservation.expired.v1` | Sales | Ticketing | Reservation expired without payment |

## MARKET stream

Wildcard: `market.>`

The resale marketplace lives in the sales service but publishes under its own prefix, so it gets its own stream.

| Subject | Published by | Consumed by | Description |
|---|---|---|---|
| `market.ticket.freeze.v1` | Sales | Ticketing | Ticket put on sale, so it must stop being usable at the door |
| `market.transfer.v1` | Sales | Ticketing | Ticket ownership moved to the buyer |
| `market.listing.expired.v1` | Sales | Ticketing | Listing expired without a buyer, so the ticket returns to its holder |
| `market.assignment.created.v1` | Sales | | Listing matched to a queued buyer |

## PAYMENTS stream

Wildcard: `payments.>`

| Subject | Published by | Consumed by | Description |
|---|---|---|---|
| `payments.payment.initiated.v1` | Payments | | Payment intent created with Stripe |
| `payments.payment.succeeded.v1` | Payments | Identity, Sales | Payment confirmed by Stripe webhook |
| `payments.payment.failed.v1` | Payments | Identity | Payment failed |
| `payments.payment.refunded.v1` | Payments | Identity, Sales | Payment refunded |
| `payments.chargeback.opened.v1` | Payments | Identity, Sales | Chargeback dispute opened |
| `payments.chargeback.closed.v1` | Payments | Identity | Chargeback dispute closed |

## ticketing stream

Wildcard: `ticketing.>`

The stream name is lowercase, unlike every other one, because the entry subscriber that creates it spells it that way. These two subjects also carry no `.v1` suffix.

| Subject | Published by | Consumed by | Description |
|---|---|---|---|
| `ticketing.ticket.state_changed` | Ticketing | Entry | Ticket state transition occurred |
| `ticketing.ticket.restored` | Ticketing | | Frozen ticket rebound to a device the holder re-enrolled |

## AUDIT stream

Wildcard: `audit.>`

| Subject | Published by | Consumed by | Description |
|---|---|---|---|
| `audit.events.v1` | Identity, Catalog, Sales, Ticketing, Entry | Audit | Security and business audit record. Payments and the Gateway write no audit records |

## GATEWAY stream

Wildcard: `ws.>`

| Subject | Published by | Consumed by | Description |
|---|---|---|---|
| `ws.fanout.v1` | Identity, Entry | Gateway | Real-time notification to be forwarded over WebSocket |

## Contract schemas

`packages/contracts/openapi/<service>/events/` is generated from `packages/contracts/src/contracts/events/` by `scripts/export-openapi.sh`, and it now holds exactly one schema per domain subject listed above, named after the class that declares it. Each class carries the subject it belongs to in a `SUBJECT` class constant.

The `market.*` shapes are declared in `contracts.events.sales`, because Sales is the service that publishes them, so they are exported to `packages/contracts/openapi/sales/events/`.

Three subjects above deliberately have no schema:

| Subject | Why |
|---|---|
| `audit.events.v1` | Audit record rather than a domain event, and its payload is the writing service's own audit row |
| `ws.fanout.v1` | Real-time notification envelope for the Gateway, not a domain event |
| `catalog.event.draft.v1` | Subscribers exist but no code publishes it, so there is no payload to describe |

Entry publishes no domain events, so it has no events module and no `events/` directory.
