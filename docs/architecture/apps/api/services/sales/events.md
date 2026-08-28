# Sales Event Contracts

Published to stream `SALES`. All events wrap the [EventEnvelope](../../messaging/messaging.md#eventenvelope).


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


## `sales.reservation.paid.v1`

Emitted after Sales confirms a payment and marks the reservation as paid. Ticketing issues the ticket.

| Field | Type | Description |
|---|---|---|
| `reservation_id` | UUID | Paid reservation |
| `payment_id` | UUID | Associated payment |


## `sales.reservation.cancelled.v1`

Emitted when a reservation is cancelled or expires. Ticketing cancels the associated ticket.

| Field | Type | Description |
|---|---|---|
| `reservation_id` | UUID | Cancelled reservation |
| `reason` | string | Cancellation reason |


## `sales.reservation.expired.v1`

Emitted by the reservation sweeper when a reservation times out before payment. Ticketing reacts by releasing whatever it had held for it.

| Field | Type | Description |
|---|---|---|
| `reservation_id` | UUID | Expired reservation |
| `user_id` | UUID | Owner of the reservation |
| `event_id` | UUID | Event the reservation belonged to |
| `ticket_type_id` | UUID | Ticket type released |
| `quantity` | integer | Seats returned to the inventory |
