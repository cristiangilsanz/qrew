# Environment Variables

All configuration lives in `config/local.yaml` per service, plus a `.env.local` file for the frontend.

---

## Frontend

File: `apps/app/.env.local`

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | `""` | Base URL for API calls. In dev Vite proxies to `localhost:8000` instead. |
| `VITE_GATEWAY_URL` | `""` | WebSocket gateway URL. In dev Vite proxies `/ws`. |
| `VITE_GOOGLE_MAPS_API_KEY` | `""` | Maps embed on venue pages |
| `VITE_STRIPE_PUBLISHABLE_KEY` | `""` | Stripe payment element |
| `VITE_TURNSTILE_SITE_KEY` | `""` | Cloudflare Turnstile CAPTCHA |

---

## Gateway

File: `apps/api/gateway/config/local.yaml`

| Key | Required | Purpose |
|---|---|---|
| `port` | yes | Listening port, default `8000` |
| `nats_url` | yes | NATS connection string |
| `redis_url` | yes | Redis connection string |
| `access_jwt_private_key` | yes | ES256 private key for JWT validation |
| `scanner_jwt_private_key` | yes | Separate key for scanner tokens |
| `jwt_audience` | no | Expected `aud` claim |
| `jwt_issuer` | no | Expected `iss` claim |
| `identity_url` | yes | Upstream identity service URL |
| `catalog_url` | yes | Upstream catalog service URL |
| `sales_url` | yes | Upstream sales service URL |
| `payments_url` | yes | Upstream payments service URL |
| `ticketing_url` | yes | Upstream ticketing service URL |
| `entry_url` | yes | Upstream entry service URL |

---

## Identity service

File: `apps/api/services/identity/config/local.yaml`

### Core

| Key | Required | Purpose |
|---|---|---|
| `port` | yes | Listening port, default `8001` |
| `database_url` | yes | PostgreSQL connection string |
| `redis_url` | yes | Redis connection string |
| `nats_url` | yes | NATS connection string |

### JWT keys

| Key | Required | Purpose |
|---|---|---|
| `access_jwt_private_key` | yes | ES256 private key for access tokens |
| `setup_jwt_private_key` | yes | Key for account setup tokens |
| `recovery_jwt_private_key` | yes | Key for password recovery tokens |
| `refresh_jwt_private_key` | yes | Key for refresh tokens |
| `queue_jwt_private_key` | yes | Key for queue position tokens |
| `ticket_qr_jwt_private_key` | yes | Key for ticket QR tokens |

### Encryption

| Key | Required | Purpose |
|---|---|---|
| `pii_encryption_key` | yes | Fernet key for names, emails, phone numbers |
| `national_id_encryption_key` | yes | Fernet key for KYC documents |

### Email

| Key | Required | Purpose |
|---|---|---|
| `smtp_enabled` | no | Enable email delivery, default `false` |
| `smtp_host` | no | SMTP server host |
| `smtp_port` | no | SMTP server port, default `587` |
| `smtp_user` | no | SMTP username |
| `smtp_password` | no | SMTP password |
| `smtp_from_address` | no | From address for outbound emails |

### SMS

| Key | Required | Purpose |
|---|---|---|
| `twilio_enabled` | no | Enable SMS delivery, default `false` |
| `twilio_account_sid` | no | Twilio account SID |
| `twilio_auth_token` | no | Twilio auth token |
| `twilio_from_number` | no | Twilio sending number |

### WebAuthn

| Key | Required | Purpose |
|---|---|---|
| `rp_id` | yes | Relying party ID, e.g. `localhost` |
| `rp_name` | yes | Relying party name shown to users |
| `rp_expected_origin` | yes | Expected origin for passkey verification |

### CAPTCHA

| Key | Required | Purpose |
|---|---|---|
| `captcha_enabled` | no | Enable Turnstile validation, default `false` |
| `captcha_secret_key` | no | Cloudflare Turnstile secret key |

### GeoIP

| Key | Required | Purpose |
|---|---|---|
| `geoip_db_path` | no | Path to MaxMind GeoLite2 database |

### Storage

| Key | Required | Purpose |
|---|---|---|
| `storage_root` | yes | Local directory for KYC document uploads |
| `storage_signing_key` | yes | Key for signed storage URLs |

---

## Catalog service

File: `apps/api/services/catalog/config/local.yaml`

| Key | Required | Purpose |
|---|---|---|
| `port` | yes | Listening port, default `8002` |
| `database_url` | yes | PostgreSQL connection string |
| `redis_url` | yes | Redis connection string |
| `nats_url` | yes | NATS connection string |
| `access_jwt_private_key` | yes | ES256 public key for token verification |
| `pii_encryption_key` | yes | Fernet key matching identity service |

---

## Sales service

File: `apps/api/services/sales/config/local.yaml`

| Key | Required | Purpose |
|---|---|---|
| `port` | yes | Listening port, default `8003` |
| `database_url` | yes | PostgreSQL connection string |
| `redis_url` | yes | Redis connection string |
| `nats_url` | yes | NATS connection string |

---

## Payments service

File: `apps/api/services/payments/config/local.yaml`

| Key | Required | Purpose |
|---|---|---|
| `port` | yes | Listening port, default `8004` |
| `database_url` | yes | PostgreSQL connection string |
| `redis_url` | yes | Redis connection string |
| `nats_url` | yes | NATS connection string |
| `stripe_secret_key` | yes | Stripe secret key |
| `stripe_webhook_signing_secret` | yes | Stripe webhook signing secret |
| `stripe_api_version` | yes | Stripe API version to pin |
| `pii_encryption_key` | yes | Fernet key matching identity service |

---

## Ticketing service

File: `apps/api/services/ticketing/config/local.yaml`

| Key | Required | Purpose |
|---|---|---|
| `port` | yes | Listening port, default `8005` |
| `database_url` | yes | PostgreSQL connection string |
| `redis_url` | yes | Redis connection string |
| `nats_url` | yes | NATS connection string |
| `ticket_qr_jwt_private_key` | yes | Key for signing QR code tokens |

---

## Entry service

File: `apps/api/services/entry/config/local.yaml`

| Key | Required | Purpose |
|---|---|---|
| `port` | yes | Listening port, default `8006` |
| `database_url` | yes | PostgreSQL connection string |
| `redis_url` | yes | Redis connection string |
| `nats_url` | yes | NATS connection string |
| `scanner_jwt_private_key` | yes | Key for issuing scanner session tokens |
| `ticket_qr_jwt_private_key` | yes | Key for verifying QR code tokens |

---

## Audit service

File: `apps/api/services/audit/config/local.yaml`

| Key | Required | Purpose |
|---|---|---|
| `port` | yes | Listening port, default `8007` |
| `database_url` | yes | PostgreSQL connection string |
| `nats_url` | yes | NATS connection string |

---

## Shared settings

Every service shares the following optional settings:

| Key | Default | Purpose |
|---|---|---|
| `debug` | `false` | Enable debug mode and detailed error responses |
| `otel_enabled` | `false` | Enable OpenTelemetry tracing |
| `otel_endpoint` | `http://localhost:4317` | OTLP collector endpoint |
| `idempotency_enabled` | `true` | Enable idempotency key enforcement |
| `ratelimit_enabled` | `true` | Enable rate limiting |

---

## Generating keys

ES256 private key:

```bash
python3 -c "
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
k = ec.generate_private_key(ec.SECP256R1())
print(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode())
"
```

Fernet key:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

The same `access_jwt_private_key` value must be used in both the identity service and the gateway. The gateway uses it only for verification. All other services do not use this key. The gateway forwards user identity via trusted headers instead.
