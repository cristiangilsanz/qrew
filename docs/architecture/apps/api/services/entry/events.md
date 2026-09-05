# Entry Event Contracts

Entry does not publish domain events to other services.

It consumes `ticketing.ticket.state_changed` to maintain its local ticket projection, and publishes audit records to `audit.events.v1`. It also publishes `ws.fanout.v1` on every scan outcome, admitted or rejected, so the Gateway can push it to the organiser's open WebSocket. Those two subjects are the whole of what Entry emits.

It also consumes four catalog subjects to maintain the projections that let it authorise a request without calling catalog over HTTP:

| Subject | Stream | Durable | Projection |
|---|---|---|---|
| `catalog.event.published.v1` | `CATALOG` | `entry-catalog-catalog-event-published-v1` | Upserts `entry.event_contexts` with the organisation and venue of the event |
| `catalog.event.updated.v1` | `CATALOG` | `entry-catalog-catalog-event-updated-v1` | Upserts `entry.event_contexts` |
| `catalog.event.ongoing.v1` | `CATALOG` | `entry-catalog-catalog-event-ongoing-v1` | Upserts `entry.event_contexts` |
| `catalog.membership.changed.v1` | `CATALOG` | `entry-catalog-membership` | Upserts `entry.organisation_member_contexts`, or deletes the row when `role` is null |

A message missing `event_id` or `organisation_id`, or missing `organisation_id` or `user_id` for the membership subject, is logged and dropped rather than retried.

Scan outcomes are written to the local `scans` table and dispatched as audit records. They do not trigger downstream state changes in other services.

Because Entry publishes no domain events, the contracts package declares no event schemas for it: there is no `contracts.events.entry` module and no `packages/contracts/openapi/entry/events/` directory.
