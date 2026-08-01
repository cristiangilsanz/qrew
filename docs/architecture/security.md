# Security

Every threat surface QREW defends against, the attack it prevents, and the control in place.

## Authentication

| Threat | Attack | Control |
|---|---|---|
| Weak passwords | Account takeover via guessing or credential stuffing | zxcvbn strength estimation rejects weak passwords at registration |
| Leaked credentials | Login with passwords from known data breaches | HIBP k-anonymity API checked on registration and every login |
| Password storage breach | Plaintext or reversible passwords exposed if DB is dumped | Argon2id hashing via argon2-cffi before any password is stored |
| Missing second factor | Single-factor accounts vulnerable to phishing | Passkeys (WebAuthn) as primary factor plus TOTP as second factor |
| Token forgery | Attacker crafts or modifies a JWT to impersonate a user | ES256 asymmetric signing — private key held only by identity service; all other services verify with public key only |
| Token replay after rotation | Stolen old tokens remain valid after key rotation | kid header in JWT allows rolling key rotation without invalidating live tokens |
| Long-lived token exposure | Stolen access token grants indefinite access | Short-lived access tokens combined with refresh token rotation |
| Session proliferation | Attacker maintains many active sessions to persist access | Hard cap of 5 concurrent sessions per user; new login evicts the oldest |
| Refresh token reuse | Stolen refresh token reused after rotation | Each token refresh invalidates the previous refresh token |
| Cross-device token use | Token extracted from one device used on another | Sessions bound to the registered device UUID |
| Brute force login | Repeated login attempts against one account | Exponential lockout starting at 5 minutes per account; admin unlock endpoint |
| Automated account creation | Bots registering bulk fake accounts | Cloudflare Turnstile CAPTCHA on registration |

## Device

| Threat | Attack | Control |
|---|---|---|
| Tampered Android app | Modified APK bypasses business logic or fakes attendance | Play Integrity API attestation validated server-side before any QR token is minted |
| Multi-account abuse from one device | Single device used to hold tickets across many fake accounts | Device fingerprint registered per UUID; accounts per device threshold blocks registration |

## Anomaly Detection

| Threat | Attack | Control |
|---|---|---|
| Account takeover from stolen credentials | Login from a geographically impossible location after a recent login elsewhere | GeoIP2 resolves login IP to coordinates; haversine distance check flags impossible travel as `LOGIN_ANOMALY_DETECTED` and audits the event |

## Ticket Fraud

| Threat | Attack | Control |
|---|---|---|
| QR forgery | Attacker generates a fake QR code to gain entry | QR tokens are short-lived JWTs signed with a dedicated scanner ES256 key; entry service validates signature before admitting |
| QR sharing | One ticket holder shares their QR with multiple people | Gate evaluates ticket state — only `issued` or `scanning` tickets mint a QR; state transitions on first scan prevent reuse |
| QR theft from tampered device | Attacker extracts QR from a rooted or modified device | Attestation failure at QR mint time blocks issuance on untrusted devices |
| Out-of-area QR use | QR generated and used outside the venue geofence | Optional venue geofence check enforced at QR mint time |
| Early QR generation | QR minted days before the event and distributed | Time window check blocks minting outside the configured window before the event |
| Scalping | Bulk purchasing of tickets for resale at inflated prices | Per-event `max_tickets_per_user` cap enforced at reservation and on the resale market |
| Grey-market resale | Tickets sold outside the platform at arbitrary prices | Resale only through the platform internal resale queue; no external transfer mechanism |

## API Surface

| Threat | Attack | Control |
|---|---|---|
| Unauthenticated access | Requests without a token reach protected endpoints | AuthMiddleware at gateway validates JWT on every non-public route before proxying |
| Public route bypass | Attacker crafts a path that looks public but reaches protected data | Public route list uses compiled regex patterns matched against full method and path |
| WebSocket hijacking | Unauthenticated WebSocket connection subscribes to private channels | JWT validated at WebSocket handshake; connection closed with 4401 on failure |
| Rate abuse | High-frequency requests to exhaust resources or brute-force | slowapi per-IP rate limiting at the gateway; individual upload endpoints additionally limited at 30 per minute |
| Duplicate requests | Retry storms cause double charges or double reservations | IdempotencyMiddleware caches responses in Redis by `Idempotency-Key` and replays cached response on duplicate |
| Cross-origin requests | Malicious browser page calls the API using a victim's cookies | Strict CORS origin allowlist in gateway config; wildcard origins not permitted |
| Clickjacking and MIME sniffing | Framing the app or exploiting browser content-type inference | SecurityHeadersMiddleware adds `X-Frame-Options`, `X-Content-Type-Options` and related headers on every response |
| Open redirect via proxy | Attacker tricks the gateway into following a redirect to an external host | Gateway proxy sets `follow_redirects=False` |
| Oversized WebSocket messages | Flood the hub with large frames to exhaust memory | WebSocket messages capped at 4 096 bytes per frame |

## File Uploads

| Threat | Attack | Control |
|---|---|---|
| Arbitrary file upload | Upload a script or binary disguised as an image | Allowed MIME types validated against a per-kind allowlist before a signed URL is issued |
| Oversized upload | Upload an extremely large file to exhaust storage or bandwidth | `max_size_bytes` enforced per upload kind before the signed URL is issued |
| Unsigned upload | Direct write to storage without going through the signed URL flow | PUT and GET to local storage require a valid HMAC signature and an unexpired `expires_at` timestamp |
| Path traversal via upload key | Craft a key with `../` sequences to escape the storage prefix | `is_valid_key` rejects any key that does not match the expected path structure |
| Public access to private uploads | Serve a non-public object through the public image endpoint | Public image endpoint checks that the storage kind for the key is `event_image` before serving |

## Data

| Threat | Attack | Control |
|---|---|---|
| PII breach from DB dump | Raw personal data exposed if the database is compromised | Names, national ID, date of birth and address encrypted at rest with Fernet symmetric encryption |
| SQL injection | Attacker injects SQL through request parameters | All DB access via SQLAlchemy ORM with parameterized queries; no raw string interpolation in queries |
| Unvalidated input | Malformed or oversized payloads crash or manipulate service logic | Pydantic schemas validate every request body and query parameter at the handler boundary |

## Payments

| Threat | Attack | Control |
|---|---|---|
| Fake Stripe webhook | Attacker POST a forged payment event to credit an account | Every incoming Stripe webhook verified with the webhook signing secret before processing |
| Double payment processing | Retry from Stripe or network causes duplicate credit | Payment intent IDs treated as idempotency keys; duplicate events are ignored |

## Infrastructure

| Threat | Attack | Control |
|---|---|---|
| Direct access to internal services | Attacker bypasses the gateway and calls a domain service directly | Only the gateway exposes a public port (8000); all domain services are on the internal Docker network |
| Unauthenticated service-to-service calls | A compromised service calls another without credentials | Internal API keys required for service-to-service calls |
| Secrets committed to version control | JWT private keys or API keys accidentally pushed to the repo | All `config/local.yaml` files excluded by `.gitignore`; `secret-scan` CI workflow scans every push |

## Audit

| Event | Recorded when |
|---|---|
| `login` | Successful login |
| `login_failed` | Failed login attempt |
| `login_locked` | Account locked after repeated failures |
| `login_unlocked` | Admin clears a lockout |
| `login_compromised_password` | HIBP check finds the password in breach data |
| `login_anomaly_detected` | Impossible travel detected |
| `device_attested` | Device passes Play Integrity attestation |
| `device_attestation_failed` | Device fails attestation |
| `device_bind` | New device registered to an account |
| `device_revoke` | Single device removed from an account |
| `device_revoke_all` | All devices removed from an account |
| `password_changed` | Account password updated |
