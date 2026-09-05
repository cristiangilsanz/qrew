# Catalog Event Contracts

Published to stream `CATALOG`. All events wrap the [EventEnvelope](../../messaging/messaging.md#eventenvelope). Schemas live in [`packages/contracts/openapi/catalog/events/`](../../../../../../packages/contracts/openapi/catalog/events/).


## `catalog.event.published.v1`, `catalog.event.updated.v1`, `catalog.event.ongoing.v1`, `catalog.event.cancelled.v1`

The four lifecycle subjects carry the same snapshot of the event, built by `_event_data`, so a consumer can upsert its projection from any of them. They are emitted when the event is published, when a draft or published event's details change, when it starts, and when it is cancelled.

| Field | Type | Description |
|---|---|---|
| `event_id` | UUID | Event the change is about |
| `organisation_id` | UUID | Owning organisation |
| `venue_id` | UUID or null | Hosting venue, null while the event has none |
| `starts_at` | ISO 8601 or null | Event start time |
| `ends_at` | ISO 8601 or null | Event end time |
| `sale_starts_at` | ISO 8601 or null | Moment sales open |
| `sale_ends_at` | ISO 8601 or null | Moment sales close |
| `max_tickets_per_user` | int | Per-user purchase limit |
| `queue_required` | bool | Whether buyers must pass through the queue |
| `queue_admit_rate_per_minute` | int | Rate the queue admits buyers at |
| `latitude` | decimal string | Venue latitude, only present when the event has a venue |
| `longitude` | decimal string | Venue longitude, only present when the event has a venue |
| `geofence_radius_m` | int | Radius enforced at the gate, only present when the event has a venue |
| `timezone` | string | Venue timezone, only present when the event has a venue |

The payload carries no event name: consumers that need it read it from catalog over HTTP.


## `catalog.ticket_type.created.v1`, `catalog.ticket_type.updated.v1`

Emitted when a ticket type is added to an event and when its mutable fields change. Both carry the same snapshot, so Sales seeds and updates its inventory projection from either.

| Field | Type | Description |
|---|---|---|
| `ticket_type_id` | UUID | Ticket type the change is about |
| `event_id` | UUID | Parent event |
| `capacity` | int | Total available tickets |
| `price_cents` | int | Price in smallest currency unit |
| `currency` | string | ISO 4217 currency code |

The name and description of the tier stay out of the payload; only what Sales needs to hold inventory travels.


## `catalog.membership.changed.v1`

Emitted when an organisation's roster changes: when the organisation is created and its owner becomes the first member, when a member is invited by email, when an already known user is added, and when a member is removed. Entry projects it into `entry.organisation_member_contexts`, so it can authorise a scanner request without calling catalog.

| Field | Type | Description |
|---|---|---|
| `organisation_id` | UUID | Organisation whose roster changed |
| `user_id` | UUID | Member the change is about |
| `role` | string or null | `member`, `manager`, or `owner`. Null means the member left, and a consumer should drop the row |

The envelope carries `aggregate_type` `organisation`, `aggregate_id` set to the organisation, and `actor_id` set to the member the change is about.
