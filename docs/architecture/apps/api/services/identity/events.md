# Identity Event Contracts

Published to stream `IDENTITY`. These four are the only `identity.*` subjects Identity emits. All events wrap the [EventEnvelope](../../messaging/messaging.md#eventenvelope).

Outside its own prefix, Identity also publishes `audit.events.v1` and `ws.fanout.v1`, both straight to NATS rather than through the outbox.


## `identity.user.registered.v1`

Emitted when a new user account is successfully created.

| Field | Type | Description |
|---|---|---|
| `user_id` | UUID | Newly created user identifier |
| `registered_at` | ISO 8601 datetime | Account creation timestamp |
| `phone_e164` | string \| null | Phone number in E.164 format, used by Sales for VoIP fraud scoring |


## `identity.fingerprint.seen.v1`

Emitted when a device fingerprint is observed, used by Sales for fraud scoring.

| Field | Type | Description |
|---|---|---|
| `fingerprint_hash` | string | Device fingerprint hash |
| `occurred_at` | ISO 8601 datetime | Timestamp of the observation |


## `identity.device.attested.v1`

Emitted when a device passes hardware attestation.

| Field | Type | Description |
|---|---|---|
| `device_id` | UUID | Attested device |
| `user_id` | UUID | Owning user |
| `platform` | string | Attestation platform, e.g. android or ios |


## `identity.device.revoked.v1`

Emitted when a device is revoked by the user or an admin. Ticketing reacts by freezing any tickets bound to the device.

| Field | Type | Description |
|---|---|---|
| `device_id` | UUID | Revoked device |
| `user_id` | UUID | Owning user |
| `reason` | string | Reason for revocation |
