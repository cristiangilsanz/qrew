# Identity

> Identity service for user authentication and JWT issuance.

## Overview

Identity is the authentication and JWT issuance authority in the platform. It manages user registration, login, session lifecycle, device attestation, KYC document verification, passkey authentication, and outbound notification delivery. It does not own event, ticket, or payment data.

## Responsibilities

1. Manages user registration, email verification, and profile updates.
2. Handles password and passkey authentication via WebAuthn.
3. Controls session lifecycle and multi-device management.
4. Attests devices via Android Play Integrity and Apple App Attest.
5. Verifies KYC documents using OCR.
6. Issues JWTs for access, setup, recovery, refresh, queue, and QR token types.
7. Encrypts PII at rest and detects anomalous login patterns.
8. Delivers notifications via SMTP and Twilio SMS.
9. Does not own event, ticket, or payment data.

## HTTP API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/auth/register` | Start multi-step user registration | Public |
| `POST` | `/auth/login` | Log in with password or passkey | Public |
| `GET` | `/auth/sessions` | List active sessions | JWT |
| `DELETE` | `/auth/sessions` | Revoke all sessions | JWT |
| `POST` | `/auth/sessions` | Refresh the session token | JWT |
| `POST` | `/auth/device` | Register and attest a device | JWT |
| `GET` | `/auth/passkey` | List registered passkeys | JWT |
| `POST` | `/auth/passkey` | Register a new passkey | JWT |
| `PATCH` | `/auth/passkey` | Update passkey metadata | JWT |
| `DELETE` | `/auth/passkey` | Remove a passkey | JWT |
| `POST` | `/auth/account` | Change or verify email and phone | JWT |
| `GET` | `/auth/profile` | Get a user profile by ID | JWT |
| `GET` | `/auth/profile/me` | Get the authenticated user profile | JWT |
| `GET` | `/auth/profile/badges` | Get user badges | JWT |
| `POST` | `/auth/recovery` | Initiate account recovery | Public |
| `POST` | `/auth/setup` | Complete account setup steps | JWT |
| `POST` | `/uploads` | Upload a profile photo or KYC document | JWT |
| `PUT` | `/uploads` | Replace an existing upload | JWT |
| `GET` | `/uploads` | Retrieve a signed upload URL | JWT |
| `POST` | `/jwt/sign` | Sign a JWT on behalf of another service | Internal |
| `GET` | `/admin/users` | List users with filters | JWT |
| `POST` | `/admin/users` | Create a user as admin | JWT |
| `POST` | `/admin/kyc` | Approve or reject a KYC submission | JWT |
| `GET` | `/admin/fingerprints` | Query device fingerprints | JWT |
| `GET` | `/admin/outbox/dlq` | Inspect the outbox dead letter queue | JWT |

Full spec: [`packages/contracts/openapi/identity/openapi.yaml`](../../../../packages/contracts/openapi/identity/openapi.yaml)

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

Schemas: [`packages/contracts/openapi/identity/events/`](../../../../packages/contracts/openapi/identity/events/)

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
| `auth_cleaner` | arq job | Purges expired sessions, tokens, and OTPs. |
| `lifecycle_notifier` | arq job | Sends lifecycle emails including welcome and verification reminders. |
| `notification_deliverer` | arq job | Drains the notification queue for email and SMS delivery. |
| `outbox_drainer` | arq job | Publishes pending domain events from the transactional outbox to NATS. |
| `storage_retainer` | arq job | Enforces the KYC document retention policy and deletes documents after the configured period. |
| `catalog.event.cancelled.*` | NATS subscriber | Handles catalog event cancellation notifications. |
| `payments.*` | NATS subscriber | Handles payment outcome notifications. |

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
| `INTERNAL_API_KEY` | Shared secret for internal service-to-service calls. |
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
