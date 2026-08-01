<div align="center">
<img src="apps/app/public/logo.webp" width="500">

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Active-success.svg)

*Your event, your ticket, your phone.*

</div>

# 📝 **Description**

<div align="center">

***QREW*** is a production-grade **event ticketing platform** built as a native mobile app to make ticket fraud and speculation structurally impossible.

</div>

# 🏗️ **Architecture**

<div align="center">

```mermaid
flowchart TB
    subgraph "📱 Client"
        phone["Your Phone"]:::app
    end

    subgraph "🔀 Edge"
        gw["API Gateway"]:::edge
    end

    subgraph "⚙️ Services"
        identity["🔑 Identity"]:::svc
        catalog["📋 Catalog"]:::svc
        sales["💸 Sales"]:::svc
        ticketing["🎟️ Ticketing"]:::svc
        payments["💳 Payments"]:::svc
        entry["🚪 Entry"]:::svc
        audit["📜 Audit"]:::svc
    end

    subgraph "🗄️ Infrastructure"
        pg[("🐘 PostgreSQL")]:::db
        redis[("🔴 Redis")]:::db
        nats["⚡ NATS JetStream"]:::bus
        stripe(["💳 Stripe"]):::ext
    end

    phone -->|"HTTPS"| gw
    gw    -->|"HTTP Proxy"| identity & catalog & sales & entry

    identity & catalog & sales & entry -->|"Publish"| nats
    nats -->|"Subscribe"| ticketing & payments & audit

    identity & catalog & sales & ticketing & payments & entry --> pg
    identity & sales --> redis
    payments <-->|"Webhooks"| stripe

    classDef app  fill:#1a1a2e,color:#fff,stroke:#4455ff,stroke-width:2px,font-weight:bold
    classDef edge fill:#2a2a2a,color:#fff,stroke:#888,stroke-width:2px,font-weight:bold
    classDef svc  fill:#1a2a1a,color:#fff,stroke:#4a8a4a,stroke-width:1px
    classDef db   fill:#0f172a,color:#fff,stroke:#334155,stroke-width:1px
    classDef bus  fill:#1c1412,color:#fff,stroke:#78564e,stroke-width:1px
    classDef ext  fill:#1a1a2e,color:#fff,stroke:#555588,stroke-width:1px
```

<div align="right">

→ [Full Architecture View](docs/architecture/overview.md)

</div>

</div>

# 📁 **Project Structure**

```
QREW/
├── README.md                          # You Are Here! ⬅️
├── CONTRIBUTING.md                    # Contribution Guidelines
├── SECURITY.md                        # Security Policyarch
├── CHANGELOG.md                       # Release History
├── LICENSE                            # MIT License
├── docker-compose.yml                 # Full Local Stack
├── Justfile                           # Dev Task Runner
│
├── apps/
│   ├── app/                           # React + Capacitor Mobile App
│   │   ├── src/
│   │   │   ├── routes/                # TanStack Router Pages
│   │   │   ├── features/              # Feature Modules (Organiser, Scanner…)
│   │   │   ├── components/            # Shared UI Components
│   │   │   └── lib/                   # Utilities, Query Keys, I18n
│   │   ├── android/                   # Android Native Project
│   │   └── ios/                       # iOS Native Project
│   │
│   └── api/
│       ├── gateway/                   # FastAPI Gateway (:8000)
│       └── services/
│           ├── identity/              # Identity Service (:8001)
│           ├── catalog/               # Catalog Service (:8002)
│           ├── sales/                 # Sales Service (:8003)
│           ├── ticketing/             # Ticketing Service (:8005)
│           ├── payments/              # Payments Service (:8004)
│           ├── entry/                 # Scanner Auth, QR Validation (:8006)
│           └── audit/                 # Immutable Audit Log (:8007)
│
├── packages/
│   ├── contracts/                     # Shared API Contracts (OpenAPI)
│   ├── shared-python/                 # Shared Python Utilities
│   └── shared-ts/                     # Shared TypeScript Types
│
└── docs/
    ├── architecture/                  # System Architecture & Security
    ├── app/                           # Frontend Docs
    ├── api/                           # API & Service Docs
    └── development/                   # Local Setup Guides
```

# 🔧 **Installation**

## 📋 Requirements

- **Docker** and **Docker Compose**
- **Node.js 20+** and **npm**
- **Python 3.12+** and **uv**
- **Android Studio** or **Xcode** (For native builds)

## ⚙️ Setup Guides

| Environment | Guide |
|---|---|
| ✅ Prerequisites | [prerequisites.md](docs/development/prerequisites.md) |
| 🔑 Environment variables | [environment-variables.md](docs/development/guides/environment-variables.md) |
| 🖥️ Local · Native | [local-native.md](docs/development/setup/local-native.md) |
| 🐳 Local · Docker | [local-docker.md](docs/development/setup/local-docker.md) |
| 📲 Android · USB | [android-usb.md](docs/development/setup/android-usb.md) |
| 📱 Android · Emulator | [android-emulator.md](docs/development/setup/android-emulator.md) |

## ⚡ Quick Start

**1. Clone the repository**

```bash
git clone https://github.com/cristiangilsanz/qrew.git
cd qrew
```

**2. Set up the frontend environment**

```bash
cp apps/app/.env.example apps/app/.env
```

Open `apps/app/.env` and fill in:

| Variable | Description |
|---|---|
| `VITE_GOOGLE_MAPS_API_KEY` | Google Maps API key (venue picker) |
| `VITE_STRIPE_PUBLISHABLE_KEY` | Stripe publishable key (checkout) |
| `VITE_TURNSTILE_SITE_KEY` | Cloudflare Turnstile site key (captcha) |

**3. Set up the backend environment**

Each service has its own `local.yaml`.

Copy all examples:

```bash
for f in $(find apps/api -name "local.yaml.example"); do cp "$f" "${f%.example}"; done
```

Fill in the required secrets across all the service configuration files:

| Secret | Where | Description |
|---|---|---|
| `access_jwt_private_key` | gateway, all services | ES256 private key for token signing |
| `pii_encryption_key` | identity, payments | Fernet key for PII encryption at rest |
| `stripe_secret_key` | payments | Stripe secret key |
| `stripe_webhook_signing_secret` | payments | Stripe webhook endpoint secret |
| `twilio_account_sid` / `twilio_auth_token` | identity | SMS / OTP delivery (optional in dev) |
| `captcha_secret_key` | identity | Cloudflare Turnstile secret (optional in dev) |
| `storage_signing_key` | identity | Key for signed storage URLs |

> Most secrets can be left empty for local dev. Features that need them are disabled by default via their `*_enabled: false` flags.

**4. Spin up the full stack**

```bash
docker compose up
```

Once running, the following services will be available locally:

| Service | URL |
|---|---|
| App | `http://localhost:5173` |
| API Gateway | `http://localhost:8000` |

# 📚 **Tech Stack**

## 🗣️ Languages

- **[Python 3.12](https://www.python.org/)**
- **[TypeScript 5](https://www.typescriptlang.org/)**

## 🧩 Frameworks & Libraries

- **[React 19](https://react.dev/)**
- **[FastAPI](https://fastapi.tiangolo.com/)**
- **[Uvicorn](https://www.uvicorn.org/)**
- **[Pydantic](https://docs.pydantic.dev/)**
- **[Capacitor](https://capacitorjs.com/)**
- **[TanStack Router](https://tanstack.com/router)**
- **[TanStack Query](https://tanstack.com/query)**
- **[SQLAlchemy](https://docs.sqlalchemy.org/)**
- **[Alembic](https://alembic.sqlalchemy.org/)**
- **[Tailwind CSS](https://tailwindcss.com/)**
- **[shadcn/ui](https://ui.shadcn.com/)**
- **[Framer Motion](https://www.framer.com/motion/)**
- **[React Hook Form](https://react-hook-form.com/)**
- **[Zod](https://zod.dev/)**
- **[Zustand](https://zustand-demo.pmnd.rs/)**
- **[react-i18next](https://react.i18next.com/)**
- **[Structlog](https://www.structlog.org/)**
- **[OpenTelemetry](https://opentelemetry.io/)**

## 🗄️ Databases

- **[PostgreSQL](https://www.postgresql.org/)**
- **[Redis](https://redis.io/)**

## ⚡ Messaging & Background Jobs

- **[NATS JetStream](https://docs.nats.io/nats-concepts/jetstream)**
- **[Arq](https://arq-docs.helpmanual.io/)**
- **[Redlock](https://redis.io/docs/latest/develop/use/patterns/distributed-locks/)**

## 🔐 Security & Auth

- **[PyJWT](https://pyjwt.readthedocs.io/)**
- **[WebAuthn](https://webauthn.io/)**
- **[pyotp](https://pyauth.github.io/pyotp/)**
- **[argon2-cffi](https://argon2-cffi.readthedocs.io/)**
- **[cryptography](https://cryptography.io/)**
- **[simplewebauthn](https://simplewebauthn.dev/)**

## 💳 Third-Party Services

- **[Stripe](https://stripe.com/docs)**
- **[Twilio](https://www.twilio.com/docs)**
- **[Google Maps](https://developers.google.com/maps)**
- **[Cloudflare Turnstile](https://developers.cloudflare.com/turnstile/)**

## 🧪 Testing

- **[Vitest](https://vitest.dev/)**
- **[React Testing Library](https://testing-library.com/)**
- **[pytest](https://docs.pytest.org/)**
- **[MSW](https://mswjs.io/)**
- **[Testcontainers](https://testcontainers.com/)**

## 🔍 Code Quality

- **[Ruff](https://docs.astral.sh/ruff/)**
- **[Pyright](https://github.com/microsoft/pyright)**
- **[ESLint](https://eslint.org/)**
- **[Prettier](https://prettier.io/)**

# 🙏 **Credits & Thanks**

Thanks to the teams behind [FastAPI](https://fastapi.tiangolo.com/), [TanStack](https://tanstack.com/), [Capacitor](https://capacitorjs.com/), [NATS](https://nats.io/), and [Stripe](https://stripe.com/) for making a project like this possible.

# 📄 **License**

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

# 📞 **Get Help & Connect**

- 💬 [Start a discussion](https://github.com/cristiangilsanz/qrew/discussions)
- 🐛 [Open an issue](https://github.com/cristiangilsanz/qrew/issues)
- 📧 cristiangilsanz@gmail.com

<div align="center">
  <br>

  **Made with 💖 for the community**

  ⭐ [Star this repo](https://github.com/cristiangilsanz/qrew) · 🍴 [Fork it](https://github.com/cristiangilsanz/qrew/fork)

  <br>

  [![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/cristiangilsanz)

</div>
