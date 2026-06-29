# Catalog Event Contracts

Published to stream `CATALOG`. All events wrap the [EventEnvelope](../README.md#eventenvelope).

---

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

---

## `catalog.event.cancelled.v1`

Emitted when an event is cancelled. Sales and Ticketing cancel pending reservations and tickets in response.

| Field | Type | Description |
|---|---|---|
| `event_id` | UUID | Cancelled event |
| `reason` | string | Cancellation reason |

---

## `catalog.event.draft.v1`

Emitted when a published event is moved back to draft. Consumers revert any projections that depend on published state.

| Field | Type | Description |
|---|---|---|
| `event_id` | UUID | Event returned to draft |

---

## `catalog.venue.created.v1`

Emitted when a new venue is created. Ticketing builds a local venue projection for geofence validation.

| Field | Type | Description |
|---|---|---|
| `venue_id` | UUID | Created venue |

---

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

---

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
