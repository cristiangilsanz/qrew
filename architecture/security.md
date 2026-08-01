# Security

A reference for every threat surface QREW defends against and the specific controls in place.

---

## Authentication

### Password security

- **Argon2id hashing** — all passwords hashed with argon2-cffi before storage
- **zxcvbn strength estimation** — weak passwords rejected at registration
- **HIBP breach check** — passwords checked against Have I Been Pwned k-anonymity API on registration and login; compromised passwords are blocked and audited

### Multi-factor authentication

- **Passkeys (WebAuthn)** — primary authentication method via device-bound credentials (simplewebauthn on client, py_webauthn on server)
- **TOTP** — time-based one-time passwords via pyotp as second factor

### Token model

- **ES256 asymmetric JWTs** — access tokens signed with ES256 private key held only by the identity service; all other services and the gateway verify with the public key only; private key never leaves the identity service
- **kid-based rotation** — JWT header carries a key ID allowing key rotation without invalidating all active tokens
- **Short-lived access tokens** — short expiry combined with refresh token rotation limits replay window

### Session management

- **Session cap** — maximum 5 active sessions per user (configurable); new login beyond cap evicts the oldest session
- **Refresh token rotation** — each token refresh invalidates the previous refresh token
- **Device binding** — sessions are bound to a registered device; cross-device token use is detected

---

## Device security

### Device fingerprinting

- **Device registration** — each device receives a persistent UUID stored server-side; requests carry the device ID header
- **Multi-account threshold** — a single device fingerprint registering beyond the allowed number of accounts is flagged and blocked

### Android attestation

- **Play Integrity API** — Android devices submit attestation tokens validated server-side; devices that fail attestation cannot issue QR tokens
- **Bypass UUID** — the nil UUID (`000...000`) skips attestation in dev/test environments only

---

## Anomaly detection

### Impossible travel

- **GeoIP resolution** — login requests are resolved to a latitude/longitude via GeoIP2 MaxMind database
- **Haversine distance check** — if a new login comes from a location that would require physically impossible travel speed from the previous login, the session is flagged as `LOGIN_ANOMALY_DETECTED` and audited

---

## Anti-fraud at the ticket layer

### QR token integrity

- **JWT-signed QR codes** — QR tokens are short-lived JWTs signed with a dedicated scanner ES256 key; the entry service validates the signature before admitting a holder
- **Gate policy evaluation** — before minting a QR, the ticketing service evaluates:
  - Ownership — ticket must belong to the requesting user
  - Ticket state — only `issued` or `scanning` tickets can generate a QR
  - Device attestation — attestation failure blocks QR issuance
  - Geofence — optional venue geofence check
  - Time window — QR minting only allowed within the configured window before the event

### Anti-scalping

- **Per-user ticket cap** — `max_tickets_per_user` enforced at reservation time and on the resale market; configurable per event (default 10)
- **Controlled resale market** — tickets can only be resold through the platform's internal resale queue, preventing external grey-market resale

---

## API protection

### Rate limiting

- **slowapi** — per-IP rate limiting applied at the gateway; limits are configurable and can be disabled for local dev

### Idempotency

- **IdempotencyMiddleware** — clients send an `Idempotency-Key` header; the gateway caches responses in Redis and replays them for duplicate requests, preventing double-charges or double-reservations from retries

### CORS

- **Strict origin allowlist** — `cors_origins` in gateway config; wildcard origins are not permitted in production

### Security headers

- **SecurityHeadersMiddleware** — applies `X-Content-Type-Options`, `X-Frame-Options`, and other defensive headers on every response

### Request tracing

- **RequestIDMiddleware** — every request receives a unique `X-Request-ID` for log correlation across services

---

## Data protection

### PII encryption at rest

- **Fernet symmetric encryption** — personally identifiable information (names, national ID, date of birth, address) encrypted with a Fernet key before being written to the database by the identity and payments services

### Input validation

- **Pydantic schemas on all endpoints** — all request bodies validated against strict Pydantic models before reaching service logic; no raw dict access in handlers

---

## Captcha

- **Cloudflare Turnstile** — CAPTCHA verification on registration to block automated account creation; configurable and can be disabled for local dev

---

## Audit trail

- **Immutable audit log** — every security-relevant event (`login`, `login_failed`, `login_locked`, `login_anomaly_detected`, `device_attested`, `device_attestation_failed`, `device_bind`, `device_revoke`, `password_changed`, `login_compromised_password`) is written to the audit service via NATS and stored append-only

---

## Payments

- **Stripe webhook signature verification** — all incoming Stripe webhooks verified with the signing secret before processing
- **Idempotent payment events** — payment intent IDs and idempotency keys prevent double-processing

---

## Infrastructure boundary

- **Single public port** — only the gateway exposes a public port (`8000`); all domain services run on the internal Docker network and are unreachable from outside
- **Internal service keys** — service-to-service calls use internal API keys; domain services reject unauthenticated internal requests

---

## Secrets management

- **Local secrets in `config/local.yaml`** — never committed; excluded by `.gitignore` (`**/config/local.yaml`)
- **Required secrets**: ES256 JWT private key, Fernet PII encryption key, Stripe secret key and webhook signing secret, Twilio credentials (SMS/OTP), Cloudflare Turnstile secret, storage signing key
