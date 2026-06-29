# Ticketing Event Contracts

Ticketing publishes to subjects not covered by a dedicated named stream. All events wrap the [EventEnvelope](../README.md#eventenvelope).

---

## `ticketing.ticket.state_changed`

Emitted on every ticket state transition. Entry maintains a local `ticket_contexts` projection from this stream.

| Field | Type | Description |
|---|---|---|
| `ticket_id` | UUID | Affected ticket |
| `event_id` | UUID | Event the ticket belongs to |
| `ticket_type_id` | UUID | Ticket type |
| `owner_user_id` | UUID | Ticket owner |
| `bound_device_id` | UUID or null | Device bound to this ticket, if any |
| `state` | string | New state (reserved, issued, entry_pending, used, cancelled, frozen, flagged) |

---

## `ticketing.ticket.restored`

Emitted when a previously frozen ticket is restored after a device re-enrolment.

| Field | Type | Description |
|---|---|---|
| `ticket_id` | UUID | Restored ticket |
| `user_id` | UUID | Ticket owner |
