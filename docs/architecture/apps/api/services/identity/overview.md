# Identity

> Identity service for user authentication and JWT issuance.

## Overview

Identity is the authentication and JWT issuance authority in the platform. It manages user registration, login, session lifecycle, device attestation, KYC document verification, passkey authentication, and outbound notification delivery. It does not own event, ticket, or payment data.

## Responsibilities

1. Manages user registration, email verification, and profile updates.
2. Handles password and passkey authentication via WebAuthn.
3. Controls session lifecycle and multi-device management.
4. Attests devices via Android Play Integrity and Apple App Attest.
5. Accepts a DNI, an NIE or any other identity document as the KYC document. A Spanish number is checked against its control letter and cross read from the image with OCR, while a foreign one is only checked for shape, since no control digit holds across issuing countries. Every submission is held for an administrator to approve.
6. Issues JWTs for access, setup, recovery, refresh, queue, and QR token types.
7. Encrypts PII at rest and detects anomalous login patterns.
8. Delivers notifications via SMTP and Twilio SMS.
9. Does not own event, ticket, or payment data.

## HTTP API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/auth/registration/` | Start multi-step user registration | Public |
| `POST` | `/auth/registration/verify-email` | Confirm the address with the mailed token | Public |
| `POST` | `/auth/registration/resend-email-verification` | Send the verification mail again | Public |
| `POST` | `/auth/registration/verify-phone` | Confirm the phone number with its code | JWT (setup) |
| `POST` | `/auth/registration/resend-phone-otp` | Send the phone code again | JWT (setup) |
| `POST` | `/auth/login` | Log in with password or passkey | Public |
| `POST` | `/auth/logout` | End the current session | JWT |
| `POST` | `/auth/refresh` | Exchange a refresh token for a new access token | Public |
| `GET` | `/auth/sessions` | List active sessions | JWT |
| `DELETE` | `/auth/sessions/{jti}` | Revoke one session | JWT |
| `POST` | `/auth/sessions/revoke-all` | Revoke every session | JWT |
| `GET` | `/auth/devices` | List bound devices | JWT |
| `POST` | `/auth/devices/attest` | Attest a device with the platform | JWT |
| `POST` | `/auth/devices/bind/begin` | Start binding a device | JWT |
| `POST` | `/auth/devices/bind/complete` | Finish binding a device | JWT |
| `POST` | `/auth/devices/fingerprint` | Record a device fingerprint | JWT |
| `POST` | `/auth/devices/{device_id}/revoke` | Revoke one device | JWT |
| `POST` | `/auth/devices/revoke-all` | Revoke every device | JWT |
| `GET` | `/auth/passkeys/` | List registered passkeys | JWT |
| `POST` | `/auth/passkeys/register/begin` | Start registering the account's only passkey | JWT |
| `POST` | `/auth/passkeys/register/complete` | Finish registering the account's only passkey | JWT |
| `POST` | `/auth/passkeys/authenticate/begin` | Start signing in with a passkey | Public |
| `POST` | `/auth/passkeys/authenticate/complete` | Finish signing in with a passkey | Public |
| `POST` | `/auth/passkeys/assert/begin` | Start reasserting the passkey of a session | JWT |
| `POST` | `/auth/passkeys/assert/complete` | Finish reasserting and return a stamped access token | JWT |
| `PATCH` | `/auth/passkeys/{passkey_id}` | Rename a passkey | JWT |
| `DELETE` | `/auth/passkeys/{passkey_id}` | Remove a passkey | JWT |
| `POST` | `/auth/totp/setup` | Start enrolling a second factor | JWT |
| `POST` | `/auth/totp/confirm` | Confirm the enrolled second factor | JWT |
| `POST` | `/auth/totp/verify` | Verify the second factor during login | JWT (totp) |
| `GET` | `/auth/totp/status` | Report whether a second factor is enabled | JWT |
| `DELETE` | `/auth/totp/disable` | Disable the second factor | JWT |
| `POST` | `/auth/account/change-email` | Request an email address change | JWT |
| `POST` | `/auth/account/confirm-email-change` | Confirm the new email address | Public |
| `POST` | `/auth/account/change-phone` | Request a phone number change | JWT |
| `POST` | `/auth/account/confirm-phone-change` | Confirm the new phone number | JWT |
| `POST` | `/auth/account/change-password` | Change the password | JWT |
| `POST` | `/auth/account/forgot-password` | Ask for a password reset link | Public |
| `POST` | `/auth/account/reset-password` | Reset the password with the mailed token | Public |
| `POST` | `/auth/account/delete` | Delete the account | JWT |
| `GET` | `/auth/profile/me` | Get the authenticated user profile | JWT |
| `GET` | `/auth/profile/onboarding-status` | Report which setup step remains | JWT (setup) |
| `GET` | `/auth/profile/audit` | Read the caller's own account trail | JWT |
| `POST` | `/auth/profile/users/public` | Resolve several user identifiers into public profiles | JWT |
| `POST` | `/auth/setup/kyc/upload` | Submit the identity document for review | JWT (setup) |
| `POST` | `/auth/setup/complete-setup` | Close the setup wizard and issue an access token | JWT (setup) |
| `POST` | `/auth/recovery/begin` | Start account recovery | Public |
| `POST` | `/auth/recovery/complete` | Finish account recovery | Public |
| `POST` | `/uploads/sign` | Get a signed URL for a direct upload | JWT |
| `PUT` | `/uploads/local/{key}` | Store an upload through the signed URL | Signed URL |
| `GET` | `/uploads/local/{key}` | Read a private upload through the signed URL | Signed URL |
| `GET` | `/uploads/public/{key}` | Read a public upload | Public |
| `GET` | `/admin/users` | List users with filters | JWT (admin) |
| `GET` | `/admin/users/search` | Search users | JWT (admin) |
| `POST` | `/admin/users/{user_id}/unlock` | Lift a lockout on an account | JWT (admin) |
| `POST` | `/admin/kyc/{user_id}/review` | Approve or reject a KYC submission | JWT (admin) |
| `GET` | `/admin/fingerprints/{fingerprint_hash}` | Query one device fingerprint | JWT (admin) |
| `GET` | `/admin/outbox/dlq` | Inspect the outbox dead letter queue | JWT (admin) |
| `POST` | `/_internal/users/lookup` | Resolve an email or phone into a user identifier | Internal |

Full spec: [`packages/contracts/openapi/identity/openapi.yaml`](../../../../../../packages/contracts/openapi/identity/openapi.yaml)

## Events

### Published

| Event | NATS Subject | Description |
|-------|-------------|-------------|
| `UserRegistered` | `identity.user.registered.v1` | Emitted when a new user completed registration. |
| `UserVerified` | `identity.user.verified.v1` | Emitted when a user passed KYC verification. |
| `DeviceBound` | `identity.device.attested.v1` | Emitted when a device was attested and bound to a user. |
| `DeviceRevoked` | `identity.device.revoked.v1` | Emitted when a device was revoked due to loss, theft, or policy. |
| `SessionEvicted` | `identity.session.evicted.v1` | Emitted when a session was forcibly terminated. |
| `PasskeyReasserted` | `identity.passkey.reasserted.v1` | Emitted when a passkey was re-verified on a device. |

Schemas: [`packages/contracts/openapi/identity/events/`](../../../../../../packages/contracts/openapi/identity/events/)

Every event is recorded in the `identity.event_outbox` table inside the same transaction as the change that caused it, and the `event_outbox_drainer` job publishes it afterwards. The request never talks to the broker. This table is separate from `identity.outbox`, which carries deferred arq jobs rather than domain events.

### Consumed

| Event | NATS Subject | Action |
|-------|-------------|--------|
| `EventCancelled` | `catalog.event.cancelled.v1` | Sends a cancellation notification to affected users. |
| `PaymentSucceeded` | `payments.payment.succeeded.v1` | Sends a payment confirmation notification. |
| `PaymentFailed` | `payments.payment.failed.v1` | Sends a payment failure notification. |
| `PaymentRefunded` | `payments.payment.refunded.v1` | Sends a refund notification. |
| `ChargebackOpened` | `payments.chargeback.opened.v1` | Sends a chargeback alert notification. |

## Background Workers

| Worker | Type | Description |
|--------|------|-------------|
| `auth_cleaner` | arq job, every 15 minutes | Purges expired sessions, tokens, and OTPs. |
| `lifecycle_notifier` | arq job, on demand | Sends the mails a payment, a cancellation or a device revocation calls for. |
| `notification_deliverer` | arq job, on demand | Drains the notification queue for email and SMS delivery. |
| `outbox_drainer` | arq job, every minute | Enqueues the arq jobs waiting in the `identity.outbox` table, so a job is never lost when the transaction that asked for it commits. |
| `event_outbox_drainer` | arq job, every minute | Publishes to NATS every domain event waiting in `identity.event_outbox`, retrying with backoff and parking a row after eight attempts. |
| `storage_retainer` | arq job, daily at 04:00 | Enforces the KYC document retention policy and deletes documents after the configured period. |
| `catalog.event.cancelled.*` | NATS subscriber | Handles catalog event cancellation notifications. |
| `payments.*` | NATS subscriber | Handles payment outcome notifications. |

The arq jobs run in the `identity-arq-worker` container, which consumes the `qrew:jobs:identity` queue. The NATS subscribers run in the separate `identity-worker` container.

## Internal Dependencies

| Package | Purpose |
|---------|---------|
| `contracts` | Domain event schemas |
| `db` | Async SQLAlchemy session factory |
| `exceptions` | Shared HTTP exception types |
| `idempotency` | Redis backed idempotency keys |
| `jobs` | arq job registration helpers |
| `locking` | Redis distributed locks |
| `messaging` | NATS JetStream publisher and subscriber |
| `middleware` | Request ID, correlation, and security headers |
| `observability` | OpenTelemetry setup |
| `outbox` | Transactional outbox mixin, recorder, and drainer for domain events |
| `pagination` | Cursor based pagination |
| `probes` | Liveness and readiness health endpoints |
| `ratelimit` | slowapi rate limiting |
| `worker` | arq worker bootstrap |

## External Dependencies

| Service | Purpose |
|---------|---------|
| PostgreSQL | Primary datastore |
| Redis | Sessions, rate limiting, idempotency keys, and outbox locking |
| NATS JetStream | Domain event publishing and consumption |
| SMTP server | Email notifications for registration, verification, and alerts |
| Twilio | SMS notifications and OTP delivery |
| GeoIP2 by MaxMind | IP geolocation for anomaly detection |

## Key Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection string. |
| `REDIS_URL` | Redis connection URL. |
| `NATS_URL` | NATS server address. |
| `BASE_URL` | Public base URL used in email links. |
| `CORS_ORIGINS` | Allowed CORS origins. |
| `ACCESS_JWT_PRIVATE_KEY` | EC private key for access token signing. |
| `SETUP_JWT_PRIVATE_KEY` | EC private key for setup flow tokens. |
| `RECOVERY_JWT_PRIVATE_KEY` | EC private key for account recovery tokens. |
| `REFRESH_JWT_PRIVATE_KEY` | EC private key for refresh tokens. |
| `QUEUE_JWT_PRIVATE_KEY` | EC private key for queue admission tokens. |
| `TICKET_QR_JWT_PRIVATE_KEY` | EC private key for QR ticket tokens. |
| `NATIONAL_ID_ENCRYPTION_KEY` | AES key for KYC document encryption at rest. |
| `PII_ENCRYPTION_KEY` | AES key for PII field encryption. |
| `INTERNAL_API_KEY` | Shared secret for internal service to service calls. |
| `STORAGE_ROOT` | Filesystem root for uploaded files. |
| `STORAGE_SIGNING_KEY` | Key used to sign temporary storage URLs. |
| `KYC_DOCUMENT_RETENTION_DAYS` | Days before KYC documents are permanently deleted. Defaults to 30. |
| `GEOIP_DB_PATH` | Path to the MaxMind GeoLite2 `.mmdb` database file. |
| `SMTP_ENABLED` | Flag to enable SMTP email delivery. |
| `SMTP_HOST` | SMTP server hostname. |
| `SMTP_PORT` | SMTP server port. |
| `SMTP_USER` | SMTP authentication username. |
| `SMTP_PASSWORD` | SMTP authentication password. |
| `SMTP_FROM_ADDRESS` | Sender address for outgoing emails. |
| `TWILIO_ENABLED` | Flag to enable Twilio SMS delivery. |
| `TWILIO_ACCOUNT_SID` | Twilio account SID. |
| `TWILIO_AUTH_TOKEN` | Twilio auth token. |
| `TWILIO_FROM_NUMBER` | Twilio sender number. |
| `CAPTCHA_ENABLED` | Flag to enable CAPTCHA verification on registration. |
| `CAPTCHA_SECRET_KEY` | CAPTCHA provider secret key. |
| `ATTESTATION_ENABLED` | Flag to enable device attestation verification. |
| `KYC_AUTO_APPROVE` | Flag to skip manual KYC review, for development and test environments only. |
| `HIBP_ENABLED` | Flag to check passwords against HaveIBeenPwned. |
| `OTEL_ENABLED` | Flag to enable OpenTelemetry tracing. |
| `OTEL_ENDPOINT` | OTLP gRPC endpoint. Defaults to `http://localhost:4317`. |
