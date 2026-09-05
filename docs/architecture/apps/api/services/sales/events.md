# Sales Event Contracts

The `sales.*` subjects below are published to stream `SALES`. The resale marketplace lives in the same service but publishes under the `market.*` prefix, so those subjects land in stream `MARKET`. All events wrap the [EventEnvelope](../../messaging/messaging.md#eventenvelope).


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


## `market.ticket.freeze.v1`

Emitted when a ticket is listed for resale. Ticketing freezes it so it stops being usable at the door while the listing is open. The envelope carries `aggregate_type` `ticket`.

| Field | Type | Description |
|---|---|---|
| `ticket_id` | UUID | Ticket put on sale |
| `actor_id` | UUID | Seller who listed it |


## `market.transfer.v1`

Emitted when a listed ticket changes owner after the buyer pays. Ticketing moves the ownership and the holder details onto the ticket. The envelope carries `aggregate_type` `ticket`.

| Field | Type | Description |
|---|---|---|
| `ticket_id` | UUID | Transferred ticket |
| `new_owner_user_id` | UUID | Buyer who now owns the ticket |
| `holder_name` | string | Name of the person who will carry the ticket |
| `holder_document_type` | string | Identity document type of the holder |
| `holder_dni` | string | Identity document number of the holder |


## `market.listing.expired.v1`

Emitted by the `market_expirer` job when a listing runs out of time without a buyer. Ticketing unfreezes the ticket and returns it to its holder. The envelope carries `aggregate_type` `market_listing`.

| Field | Type | Description |
|---|---|---|
| `ticket_id` | UUID | Ticket whose listing expired |
| `seller_user_id` | UUID | Holder the ticket returns to |


## `market.assignment.created.v1`

Emitted when an open listing is offered to the next buyer waiting in the resale queue, both by the `market_assigner` job and by `market_expirer` when it re-offers a declined assignment. No service subscribes to it, so it is published for audit and future consumers only. The envelope carries `aggregate_type` `market_assignment`.

| Field | Type | Description |
|---|---|---|
| `assignment_id` | UUID | New assignment awaiting payment |
| `buyer_user_id` | UUID | Buyer the listing was offered to |
