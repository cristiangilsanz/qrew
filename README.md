<div align="center">
<img src="apps/app/public/logo.webp" width="500">

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
    subgraph Client["Client"]
        phone["Your Phone"]:::app
    end

    subgraph Edge["Edge"]
        gw["🔀 API Gateway"]:::edge
    end

    subgraph Domain["Domain"]
        identity["🔑 Identity"]:::svc
        catalog["📋 Catalog"]:::svc
        sales["💸 Sales"]:::svc
        payments["💳 Payments"]:::svc
        ticketing["🎟️ Ticketing"]:::svc
        entry["🚪 Entry"]:::svc
        audit["📜 Audit"]:::svc
    end

    subgraph Infra["Infrastructure"]
        pg[("🐘 PostgreSQL")]:::db
        redis[("🗃️ Redis")]:::db
        nats["📨 NATS JetStream"]:::bus
    end

    subgraph ThirdParty["Third-Party Services"]
        stripe(["💳 Stripe"]):::ext
        twilio(["📱 Twilio"]):::ext
        maps(["🗺️ Google Maps"]):::ext
        turnstile(["🛡️ Cloudflare Turnstile"]):::ext
        hibp(["🔓 HIBP"]):::ext
    end

    phone  -->|"Request"| Edge
    Edge   -->|"Forward"| Domain
    Domain -->|"Read / Write"| pg
    Domain -->|"Read / Write"| redis
    Domain <-->|"Publish / Subscribe"| nats
    identity ~~~ catalog ~~~ sales ~~~ payments ~~~ ticketing ~~~ entry ~~~ audit
    Domain <-->|"Connect"| ThirdParty

    classDef app  fill:#111,color:#fff,stroke:#fff,stroke-width:2px,font-weight:bold
    classDef edge fill:#222,color:#fff,stroke:#aaa,stroke-width:2px,font-weight:bold
    classDef svc  fill:#1a1a1a,color:#fff,stroke:#888,stroke-width:1px
    classDef db   fill:#0a0a0a,color:#fff,stroke:#666,stroke-width:1px
    classDef bus  fill:#111,color:#fff,stroke:#999,stroke-width:1px
    classDef ext  fill:#222,color:#fff,stroke:#777,stroke-width:1px
```

</div>

> [!NOTE]
> This is a simple picture of the system. The full dive into the topic is in [ARCHITECTURE.md](docs/architecture/overview.md).

# 📁 **Project Structure**

```
QREW/
├── apps/
│   ├── app/                           # Frontend (:5173)
│   │   ├── src/
│   │   │   ├── routes/
│   │   │   ├── features/
│   │   │   ├── components/
│   │   │   └── lib/
│   │   ├── android/
│   │   └── ios/
│   │
│   └── api/                           # Backend
│       ├── gateway/                   # API Gateway (:8000)
│       └── services/
│           ├── identity/              # Identity Service (:8001)
│           ├── catalog/               # Catalog Service (:8002)
│           ├── sales/                 # Sales Service (:8003)
│           ├── payments/              # Payments Service (:8004)
│           ├── ticketing/             # Ticketing Service (:8005)
│           ├── entry/                 # Entry Service (:8006)
│           └── audit/                 # Audit Service (:8007)
│
├── packages/
│   ├── contracts/
│   ├── shared-python/
│   └── shared-ts/
```

# 🔧 **Installation**

## 📋 Requirements

- **Docker** and **Docker Compose**
- **Node.js 20+** and **npm**
- **Python 3.12+** and **uv**
- **Android Studio** or **Xcode** (For native builds)

## ⚙️ Setup Guides

- ✅ [Prerequisites](docs/development/prerequisites.md)
- 🔑 [Environment Variables](docs/development/configuration.md)
- 🖥️ [Local · Native](docs/development/setup/local-native.md)
- 🐳 [Local · Docker](docs/development/setup/local-docker.md)
- 🔌 [Android · USB](docs/development/setup/android-usb.md)
- 🕹️ [Android · Emulator](docs/development/setup/android-emulator.md)

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

<div align="center">

| Variable | Description |
|---|---|
| `VITE_GOOGLE_MAPS_API_KEY` | Google Maps API Key |
| `VITE_STRIPE_PUBLISHABLE_KEY` | Stripe Publishable Key |
| `VITE_TURNSTILE_SITE_KEY` | Cloudflare Turnstile Site Key |

</div>

**3. Set up the backend environment**

Each service has its own `local.yaml`.

Copy all examples:

```bash
for f in $(find apps/api -name "local.yaml.example"); do cp "$f" "${f%.example}"; done
```

Fill in the required secrets across all the service configuration files:

<div align="center">

| Secret |
|---|
| `access_jwt_private_key` |
| `pii_encryption_key` |
| `stripe_secret_key` |
| `stripe_webhook_signing_secret` |
| `twilio_account_sid` / `twilio_auth_token` |
| `captcha_secret_key` |
| `storage_signing_key` |

</div>

> [!NOTE]
> Most secrets can be left empty for local dev. Features that need them are disabled by default via their `*_enabled: false` flags.

**4. Spin up the full stack**

```bash
docker compose up
```


# 📚 **Tech Stack**

## Languages

- [Python](https://www.python.org/)
- [TypeScript](https://www.typescriptlang.org/)

## Frameworks & Libraries

- [React](https://react.dev/)
- [Vite](https://vitejs.dev/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Uvicorn](https://www.uvicorn.org/)
- [Pydantic](https://docs.pydantic.dev/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [Tailwind CSS](https://tailwindcss.com/)
- [TanStack Router](https://tanstack.com/router)
- [TanStack Query](https://tanstack.com/query)
- [Zustand](https://zustand-demo.pmnd.rs/)
- [Immer](https://immerjs.github.io/immer/)
- [Capacitor](https://capacitorjs.com/)
- [Radix UI](https://www.radix-ui.com/)
- [Framer Motion](https://www.framer.com/motion/)
- [React Hook Form](https://react-hook-form.com/)
- [Zod](https://zod.dev/)
- [Axios](https://axios-http.com/)
- [react-i18next](https://react.i18next.com/)
- [OpenTelemetry](https://opentelemetry.io/)
- [Structlog](https://www.structlog.org/)
- [slowapi](https://slowapi.readthedocs.io/)
- [httpx](https://www.python-httpx.org/)
- [OpenCV](https://opencv.org/)
- [Pillow](https://pillow.readthedocs.io/)
- [Lucide React](https://lucide.dev/)
- [Sonner](https://sonner.emilkowal.ski/)
- [date-fns](https://date-fns.org/)

## Databases

- [PostgreSQL](https://www.postgresql.org/)
- [Redis](https://redis.io/)

## Infrastructure

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Jaeger](https://www.jaegertracing.io/)

## Messaging & Background Jobs

- [NATS JetStream](https://docs.nats.io/nats-concepts/jetstream)
- [Arq](https://arq-docs.helpmanual.io/)

## Security & Auth

- [cryptography](https://cryptography.io/)
- [Passlib](https://passlib.readthedocs.io/)
- [argon2-cffi](https://argon2-cffi.readthedocs.io/)
- [PyJWT](https://pyjwt.readthedocs.io/)
- [SimpleWebAuthn](https://simplewebauthn.dev/)
- [pyotp](https://pyauth.github.io/pyotp/)

## Third-Party Services

- [Stripe](https://stripe.com/docs)
- [Twilio](https://www.twilio.com/docs)
- [Google Maps](https://developers.google.com/maps)
- [Cloudflare Turnstile](https://developers.cloudflare.com/turnstile/)
- [HIBP](https://haveibeenpwned.com/API/v3)

## Testing

- [pytest](https://docs.pytest.org/)
- [Vitest](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/)
- [Testcontainers](https://testcontainers.com/)
- [MSW](https://mswjs.io/)

## Code Quality

- [Pyright](https://github.com/microsoft/pyright)
- [ESLint](https://eslint.org/)
- [Ruff](https://docs.astral.sh/ruff/)
- [Prettier](https://prettier.io/)

## Tooling

- [GitHub Actions](https://docs.github.com/en/actions)
- [just](https://just.systems/)
- [uv](https://docs.astral.sh/uv/)
- [Husky](https://typicode.github.io/husky/)
- [commitlint](https://commitlint.js.org/)
- [pre-commit](https://pre-commit.com/)

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
