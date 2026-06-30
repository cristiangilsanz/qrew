# Identity Event Contracts

Published to stream `IDENTITY`. All events wrap the [EventEnvelope](../README.md#eventenvelope).

---

## `identity.user.registered.v1`

Emitted when a new user account is successfully created.

| Field | Type | Description |
|---|---|---|
| `email` | string | Registered email address |
| `display_name` | string | User full name |

---

## `identity.fingerprint.seen.v1`

Emitted when a device fingerprint is observed during login, used by Sales for fraud scoring.

| Field | Type | Description |
|---|---|---|
| `user_id` | UUID | User who authenticated |

---

## `identity.device.attested.v1`

Emitted when a device passes hardware attestation.

| Field | Type | Description |
|---|---|---|
| `device_id` | UUID | Attested device |
| `user_id` | UUID | Owning user |
| `platform` | string | Attestation platform (e.g. android, ios) |

---

## `identity.device.revoked.v1`

Emitted when a device is revoked by the user or an admin. Ticketing reacts by freezing any tickets bound to the device.

| Field | Type | Description |
|---|---|---|
| `device_id` | UUID | Revoked device |
| `user_id` | UUID | Owning user |
| `reason` | string | Reason for revocation |
