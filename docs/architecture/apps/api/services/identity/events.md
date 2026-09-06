# Identity Event Contracts

Published to stream `IDENTITY`. These four are the only `identity.*` subjects Identity emits. All events wrap the [EventEnvelope](../../messaging/messaging.md#eventenvelope). Schemas live in [`packages/contracts/openapi/identity/events/`](../../../../../../packages/contracts/openapi/identity/events/).

Outside its own prefix, Identity also publishes `audit.events.v1` and `ws.fanout.v1`, both straight to NATS rather than through the outbox.


## `identity.user.registered.v1`

Emitted when a new user account is successfully created.

| Field | Type | Description |
|---|---|---|
| `user_id` | UUID | Newly created user identifier |
| `registered_at` | ISO 8601 datetime | Account creation timestamp |
| `phone_e164` | string or null | Phone number in E.164 format, used by Sales for VoIP fraud scoring |


## `identity.fingerprint.seen.v1`

Emitted when a device fingerprint is observed, used by Sales for fraud scoring. The moment of the observation travels in the envelope's `occurred_at`, not in the payload.

| Field | Type | Description |
|---|---|---|
| `fingerprint_hash` | string | Device fingerprint hash |


## `identity.device.attested.v1`

Emitted when a device is bound, whether or not the attestation platform accepted it.

| Field | Type | Description |
|---|---|---|
| `device_id` | UUID | Attested device |
| `user_id` | UUID | Owning user |
| `attested_at` | ISO 8601 datetime | Moment the binding was recorded |
| `platform` | string or null | Attestation platform, for example `android`, `ios`, or `skipped` |


## `identity.device.revoked.v1`

Emitted when a device is revoked by the user or an admin. Ticketing reacts by freezing any tickets bound to the device.

| Field | Type | Description |
|---|---|---|
| `device_id` | UUID | Revoked device |
| `user_id` | UUID | Owning user |
| `revoked_at` | ISO 8601 datetime | Moment of the revocation |
