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

## Contract schemas without a subject

`packages/contracts/openapi/*/events/` is generated from `packages/contracts/src/contracts/events/`, and both still carry event shapes from an earlier design that no service ever publishes. The registry above lists what actually travels on the wire, so treat the following schemas as declared but dormant.

| Service | Schemas with no publisher |
|---|---|
| Catalog | `OrganisationCreated`, `TicketTypeDeleted` |
| Entry | `EntryValidated`, `EntryRejected` |
| Identity | `UserVerified`, `SessionEvicted`, `PasskeyReasserted` |
| Sales | `QueueJoined`, `QueueAdmitted`, `ReservationFlagged` |
| Ticketing | `TicketIssued`, `TicketFrozen`, `TicketCancelled`, `TicketUsed`, `QrMinted`, `QrDenied` |

The gap runs the other way too. These subjects travel but have no declared schema.

| Service | Subjects with no schema |
|---|---|
| Catalog | `catalog.event.updated.v1`, `catalog.event.ongoing.v1`, `catalog.ticket_type.updated.v1`, `catalog.membership.changed.v1` |
| Identity | `identity.fingerprint.seen.v1` |
| Payments | `payments.chargeback.closed.v1` |
| Sales | `market.ticket.freeze.v1`, `market.transfer.v1`, `market.listing.expired.v1`, `market.assignment.created.v1` |
| Ticketing | `ticketing.ticket.state_changed` |

No code outside the contracts package imports any of the dormant shapes, so nothing breaks by leaving them there. They are worth either implementing or removing before the contract package is taken as a description of the system.
