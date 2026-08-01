# Local Development

Run services directly on your machine for the fastest feedback loop. All backend services hot-reload on save. The frontend uses Vite HMR.

---

## 1. Clone and set up

```bash
git clone https://github.com/cristiangilsanz/qrew.git
cd qrew
just setup
```

`just setup` does the following in one step:

1. Stops any running containers and removes volumes
2. Starts PostgreSQL, Redis, and NATS in Docker
3. Creates a Python virtualenv at `.venv` using Python 3.12
4. Installs all backend dependencies with `uv sync`
5. Applies all database migrations

---

## 2. Configure secrets

Copy the example configs for each service:

```bash
for svc in identity catalog sales ticketing payments entry audit; do
  cp apps/api/services/$svc/config/local.yaml.example apps/api/services/$svc/config/local.yaml
done
cp apps/api/gateway/config/local.yaml.example apps/api/gateway/config/local.yaml
```

Most keys can stay empty for local work. Services will start without them. The following are required for specific features:

| Key | Service | Feature |
|---|---|---|
| `access_jwt_private_key` | identity | Login and token issuance |
| `pii_encryption_key` | identity | User PII storage |
| `stripe_secret_key` | payments | Payments flow |
| `twilio_*` | identity | Phone OTP |
| `smtp_*` | identity | Email delivery |

For the JWT and Fernet keys, generate them once:

```bash
# ES256 private key for JWT signing
python3 -c "from cryptography.hazmat.primitives.asymmetric import ec; from cryptography.hazmat.primitives import serialization; k = ec.generate_private_key(ec.SECP256R1()); print(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode())"

# Fernet key for PII encryption
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Configure the frontend:

```bash
cp apps/app/.env.example apps/app/.env.local
npm --prefix apps/app install
```

In development `VITE_API_URL` can stay empty. Vite proxies `/api` and `/ws` to `localhost:8000`.

---

## 3. Start infrastructure

If you ran `just setup` infrastructure is already running. To resume it after a restart:

```bash
just resume
```

---

## 4. Run backend services

Open a terminal per service, or use a terminal multiplexer:

```bash
just identity-dev       # :8001
just catalog-dev        # :8002
just sales-dev          # :8003
just payments-dev       # :8004
just ticketing-dev      # :8005
just entry-dev          # :8006
just audit-dev          # :8007
just gateway-dev        # :8000
```

Background workers (start these alongside their services):

```bash
just identity-worker        # NATS worker
just identity-job-worker    # Arq job worker
just catalog-worker
just sales-worker
just ticketing-worker
just entry-worker
just audit-worker
```

Workers are only needed when testing flows that cross service boundaries, such as ticket issuance after payment.

---

## 5. Run the frontend

```bash
cd apps/app
npm run dev
```

App is available at `http://localhost:5173`.

---

## 6. Seed demo data

```bash
just db-seed
```

| Email | Password | Role |
|---|---|---|
| `admin@qrew.dev` | `AdminPass1!` | Admin, all demo data |
| `user1@qrew.dev` | `Password123!` | Attendee, empty account |
| `user2@qrew.dev` | `Password123!` | Attendee, empty account |

---

## Everyday commands

| Command | What it does |
|---|---|
| `just resume` | Start infrastructure after a machine restart |
| `just stop` | Stop infrastructure containers |
| `just db-seed` | Load demo data |
| `just db-truncate` | Wipe all rows, keep schema |
| `just db-upgrade` | Apply pending migrations |
| `just fix` | Auto-fix lint and format issues |
| `just check` | Run all lint, type, and test checks |

---

## Database migrations

Generate a migration after changing a model:

```bash
just identity-migrate "add_column_name"
just catalog-migrate "add_column_name"
```

Replace the prefix with the target service. Review the generated file in `alembic/versions/` before committing.

Apply pending migrations:

```bash
just db-upgrade
```

---

## Stripe webhooks

To test the payments flow locally, forward Stripe events to the running payments service:

```bash
just stripe-dev
```

This requires the Stripe CLI to be installed and logged in. Copy the `whsec_` signing secret it prints into `apps/api/services/payments/config/local.yaml`.

---

## Troubleshooting

**Service fails to start with "connection refused"**
Infrastructure is not running. Run `just resume`.

**"alembic.util.exc.CommandError: Can't locate revision"**
Migrations are out of sync. Run `just db-clean` to reset them.

**Frontend shows "network error" on all API calls**
The gateway is not running, or it is on the wrong port. Confirm `just gateway-dev` is running on port 8000.

**"duplicate key value" on seed**
The seed is idempotent for the admin user but can fail if partial data exists. Run `just db-truncate && just db-seed` to start clean.
