# Ticketing Event Contracts

Published to stream `ticketing`, whose name is lowercase because the entry subscriber that creates it spells it that way. These are the only two subjects Ticketing publishes, and neither carries a `.v1` suffix. All events wrap the [EventEnvelope](../../messaging/messaging.md#eventenvelope). Schemas live in [`packages/contracts/openapi/ticketing/events/`](../../../../../../packages/contracts/openapi/ticketing/events/).

Ticketing also publishes audit records to `audit.events.v1`.


## `ticketing.ticket.state_changed`

Emitted on every ticket state transition. Entry maintains a local `ticket_contexts` projection from this stream.

| Field | Type | Description |
|---|---|---|
| `ticket_id` | UUID | Affected ticket |
| `event_id` | UUID | Event the ticket belongs to |
| `state` | string | New state: `reserved`, `issued`, `scanning`, `redeemed`, `on_sale`, `frozen`, `flagged`, `cancelled`, `expired` |
| `previous_state` | string | State the ticket held before the transition |
| `owner_user_id` | UUID | Ticket owner |
| `bound_device_id` | UUID or null | Device bound to this ticket, if any |


## `ticketing.ticket.restored`

Emitted when a previously frozen ticket is restored after a device re-enrolment. No service subscribes to it.

| Field | Type | Description |
|---|---|---|
| `ticket_id` | UUID | Restored ticket |
| `user_id` | UUID | Ticket owner |
