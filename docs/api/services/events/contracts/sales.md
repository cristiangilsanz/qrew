# Sales Event Contracts

Published to stream `SALES`. All events wrap the [EventEnvelope](../README.md#eventenvelope).

---

## `sales.reservation.created.v1`

Emitted when a reservation is successfully placed. Ticketing pre-creates a ticket record in `reserved` state.

| Field | Type | Description |
|---|---|---|
| `reservation_id` | UUID | New reservation |
| `user_id` | UUID | Purchasing user |
| `ticket_type_id` | UUID | Ticket type reserved |
| `event_id` | UUID | Target event |
| `quantity` | int | Number of tickets |
| `expires_at` | ISO 8601 | Reservation expiry time |

---

## `sales.reservation.paid.v1`

Emitted after Sales confirms a payment and marks the reservation as paid. Ticketing issues the ticket.

| Field | Type | Description |
|---|---|---|
| `reservation_id` | UUID | Paid reservation |
| `payment_id` | UUID | Associated payment |

---

## `sales.reservation.cancelled.v1`

Emitted when a reservation is cancelled or expires. Ticketing cancels the associated ticket.

| Field | Type | Description |
|---|---|---|
| `reservation_id` | UUID | Cancelled reservation |
| `reason` | string | Cancellation reason |
