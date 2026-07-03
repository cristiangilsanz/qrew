# Entry Event Contracts

Entry does not publish domain events to other services.

It consumes `ticketing.ticket.state_changed` to maintain its local ticket projection, and publishes audit records to `audit.events.v1` like every other service.

Scan outcomes (`EntryValidatedData`, `EntryRejectedData`) are written to the local `scans` table and dispatched as audit events.

They do not trigger downstream state changes in other services.
