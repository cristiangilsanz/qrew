# Catalog Event Contracts

Published to stream `CATALOG`. All events wrap the [EventEnvelope](../../messaging/messaging.md#eventenvelope).


## `catalog.event.published.v1`

Emitted when an event moves from draft to published state.

| Field | Type | Description |
|---|---|---|
| `event_id` | UUID | Published event |
| `organisation_id` | UUID | Owning organisation |
| `venue_id` | UUID | Hosting venue |
| `name` | string | Event name |
| `starts_at` | ISO 8601 | Event start time |
| `ends_at` | ISO 8601 | Event end time |
| `latitude` | decimal string | Venue latitude, when the event has a venue |
| `longitude` | decimal string | Venue longitude, when the event has a venue |
| `geofence_radius_m` | integer | Radius Ticketing enforces at the gate |
| `timezone` | string | Venue timezone |


## `catalog.event.cancelled.v1`

Emitted when an event is cancelled. Sales and Ticketing cancel pending reservations and tickets in response.

| Field | Type | Description |
|---|---|---|
| `event_id` | UUID | Cancelled event |
| `reason` | string | Cancellation reason |


## `catalog.event.updated.v1`

Emitted when a draft or published event's details are changed.

| Field | Type | Description |
|---|---|---|
| `event_id` | UUID | Updated event |


## `catalog.event.ongoing.v1`

Emitted when an event is manually marked as started by an organiser.

| Field | Type | Description |
|---|---|---|
| `event_id` | UUID | Event now in ongoing state |


## `catalog.ticket_type.created.v1`

Emitted when a ticket type is added to an event. Sales seeds its inventory projection.

| Field | Type | Description |
|---|---|---|
| `ticket_type_id` | UUID | New ticket type |
| `event_id` | UUID | Parent event |
| `name` | string | Ticket type name |
| `price_cents` | int | Price in smallest currency unit |
| `currency` | string | ISO 4217 currency code |
| `capacity` | int | Total available tickets |


## `catalog.ticket_type.updated.v1`

Emitted when a ticket type's capacity or price changes. Sales updates its inventory projection.

| Field | Type | Description |
|---|---|---|
| `ticket_type_id` | UUID | Updated ticket type |
| `event_id` | UUID | Parent event |
| `name` | string | Ticket type name |
| `price_cents` | int | Updated price |
| `currency` | string | ISO 4217 currency code |
| `capacity` | int | Updated capacity |
