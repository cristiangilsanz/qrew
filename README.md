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

***QREW*** is a production-grade **event ticketing platform** built as a native mobile app. Built to make ticket fraud and speculation structurally impossible.

Zero friction. One product. Three roles.

</div>

# 🏗️ **Architecture**

<div align="center">

```mermaid
flowchart TB
    app["📱 Mobile App\nReact + Capacitor"]:::nodeStyle

    subgraph Edge
        gw["🔀 API Gateway\nJWT validation + reverse proxy"]:::nodeStyle
    end

    subgraph Services
        identity["🔑 Identity"]:::nodeStyle
        catalog["📋 Catalog"]:::nodeStyle
        sales["💸 Sales"]:::nodeStyle
        ticketing["🎟️ Ticketing"]:::nodeStyle
        payments["💳 Payments"]:::nodeStyle
        entry["🚪 Entry"]:::nodeStyle
        audit["📜 Audit"]:::nodeStyle
    end

    subgraph Infrastructure
        pg[("🐘 PostgreSQL 16")]:::infraStyle
        nats["⚡ NATS JetStream\nEvent bus"]:::infraStyle
        redis[("🔴 Redis\nCache · Locks · Jobs")]:::infraStyle
        stripe(["💳 Stripe"]):::infraStyle
    end

    app -->|"HTTPS"| gw
    gw -->|"HTTP proxy"| identity
    gw -->|"HTTP proxy"| catalog
    gw -->|"HTTP proxy"| sales
    gw -->|"HTTP proxy"| entry
    catalog <-->|"Domain events"| nats
    sales <-->|"Domain events"| nats
    entry <-->|"Domain events"| nats
    nats --> ticketing
    nats --> payments
    nats --> audit
    identity --> pg
    catalog --> pg
    sales --> pg
    ticketing --> pg
    payments --> pg
    identity --> redis
    sales --> redis
    payments <-->|"Webhooks"| stripe

    classDef nodeStyle fill:#333333,color:#ffffff,stroke:#555555,stroke-width:2px,font-weight:bold
    classDef infraStyle fill:#1a1a2e,color:#ffffff,stroke:#555555,stroke-width:2px,font-weight:bold
```

</div>

---

# 📁 **Project Structure**

```
QREW/
├── README.md                          # You are here! ⬅️
├── ARCHITECTURE.md                    # System architecture deep-dive
├── CONTRIBUTING.md                    # Contribution guidelines
├── SECURITY.md                        # Security policy
├── CHANGELOG.md                       # Release history
├── LICENSE                            # MIT License
├── docker-compose.yml                 # Full local stack
├── Justfile                           # Dev task runner
│
├── apps/
│   ├── app/                           # React + Capacitor mobile app
│   │   ├── src/
│   │   │   ├── routes/                # TanStack Router pages
│   │   │   ├── features/              # Feature modules (organiser, scanner…)
│   │   │   ├── components/            # Shared UI components
│   │   │   └── lib/                   # Utilities, query keys, i18n
│   │   ├── android/                   # Android native project
│   │   └── ios/                       # iOS native project
│   │
│   └── api/
│       ├── gateway/                   # Starlette API gateway (:8000)
│       └── services/
│           ├── identity/              # Auth, users, passkeys, TOTP, KYC
│           ├── catalog/               # Events, venues, organisations
│           ├── sales/                 # Reservations, resale market, queue
│           ├── ticketing/             # Tickets, QR tokens
│           ├── payments/              # Stripe webhooks + disbursements
│           ├── entry/                 # Scanner auth, QR validation
│           └── audit/                 # Immutable audit log
│
├── packages/
│   ├── contracts/                     # Shared API contracts (OpenAPI)
│   ├── shared-python/                 # Shared Python utilities
│   └── shared-ts/                     # Shared TypeScript types
│
└── docs/
    ├── app/                           # Frontend docs
    ├── api/                           # API & service docs
    └── development/                   # Local setup guides
```

---

# 🔧 **Installation**

## 📋 Requirements

- **Docker** and **Docker Compose**
- **Node.js 20+** and **npm**
- **Python 3.12+** and **uv**
- **Android Studio** or **Xcode** (For native builds)

## ⚙️ Setup Guides

| Environment | Guide |
|---|---|
| 🖥️ Local (terminal) | [LOCAL-DEVELOPMENT.md](docs/development/LOCAL-DEVELOPMENT.md) |
| 🐳 Local (containers) | [DOCKER.md](docs/development/DOCKER.md) |
| 📱 Android emulator | [EMULATOR.md](docs/development/EMULATOR.md) |
| 📲 Physical device (USB) | [DEVICE.md](docs/development/DEVICE.md) |
| 🔑 Environment variables | [ENVIRONMENT-VARIABLES.md](docs/development/ENVIRONMENT-VARIABLES.md) |
| ✅ Prerequisites | [PREREQUISITES.md](docs/development/PREREQUISITES.md) |

## ⚡ Quick Start (Docker)

```bash
git clone https://github.com/cristiangilsanz/qrew.git
cd qrew  # the repo folder is lowercase

# Copy env files and fill in your secrets
cp apps/app/.env.example apps/app/.env

# Spin up the full stack
docker compose up
```

The app will be available at `http://localhost:5173`.

---

# 📚 **Tech Stack**

## 📱 Frontend

| | Technology |
|---|---|
| Framework | [React 18](https://react.dev/) |
| Routing | [TanStack Router](https://tanstack.com/router) |
| Data fetching | [TanStack Query](https://tanstack.com/query) |
| Styling | [Tailwind CSS](https://tailwindcss.com/) |
| Components | [shadcn/ui](https://ui.shadcn.com/) |
| Animations | [Framer Motion](https://www.framer.com/motion/) |
| Internationalisation | [react-i18next](https://react.i18next.com/) |

## 📲 Native

| | Technology |
|---|---|
| Runtime | [Capacitor](https://capacitorjs.com/) |
| Platforms | Android · iOS |

## 🔀 API Gateway

| | Technology |
|---|---|
| Framework | [Starlette](https://www.starlette.io/) |
| Responsibility | JWT validation · reverse proxy |

## ⚙️ Backend Services

| | Technology |
|---|---|
| Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| ORM | [SQLAlchemy](https://docs.sqlalchemy.org/) |
| Migrations | [Alembic](https://alembic.sqlalchemy.org/) |

## 🔐 Auth & Security

| | Technology |
|---|---|
| Token signing | JWT ES256 |
| Passwordless | [WebAuthn passkeys](https://webauthn.io/) |
| 2FA | TOTP |
| Password hashing | Argon2 |
| PII encryption | Fernet |

## ⚡ Messaging & Jobs

| | Technology |
|---|---|
| Event bus | [NATS JetStream](https://docs.nats.io/nats-concepts/jetstream) |
| Background jobs | [Arq](https://arq-docs.helpmanual.io/) |
| Distributed locks | [Redlock](https://redis.io/docs/latest/develop/use/patterns/distributed-locks/) |

## 🗃️ Data

| | Technology |
|---|---|
| Database | [PostgreSQL 16](https://www.postgresql.org/) |
| Cache | [Redis](https://redis.io/) |

## 🌐 External Services

| | Technology |
|---|---|
| Payments | [Stripe](https://stripe.com/docs) |
| Email | [Resend](https://resend.com/docs) |
| SMS / OTP | [Twilio](https://www.twilio.com/docs) |
| Object storage | [Cloudflare R2](https://developers.cloudflare.com/r2/) |

## 🧪 Testing

| | Technology |
|---|---|
| Frontend unit tests | [Vitest](https://vitest.dev/) + [React Testing Library](https://testing-library.com/) |
| Backend unit tests | [pytest](https://docs.pytest.org/) |
| API mocking | [MSW](https://mswjs.io/) |

## 🔍 Code Quality

| | Technology |
|---|---|
| Python linting + formatting | [ruff](https://docs.astral.sh/ruff/) |
| Python type checking | [pyright](https://github.com/microsoft/pyright) |
| TypeScript linting | [eslint](https://eslint.org/) |
| TypeScript formatting | [prettier](https://prettier.io/) |

---

# 📖 **Documentation**

| Topic | Link |
|---|---|
| 🏗️ Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 🗺️ App routing | [docs/app/ROUTING.md](docs/app/ROUTING.md) |
| 🧩 Components | [docs/app/COMPONENTS.md](docs/app/COMPONENTS.md) |
| 🌍 Internationalisation | [docs/app/I18N.md](docs/app/I18N.md) |
| 📦 State management | [docs/app/STATE-MANAGEMENT.md](docs/app/STATE-MANAGEMENT.md) |
| 📱 Capacitor setup | [docs/app/CAPACITOR.md](docs/app/CAPACITOR.md) |
| 🔌 API services | [docs/api/](docs/api/) |
| ⚡ NATS streams | [docs/api/streams.md](docs/api/streams.md) |
| 🤝 Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 🔒 Security | [SECURITY.md](SECURITY.md) |
| 📋 Changelog | [CHANGELOG.md](CHANGELOG.md) |

---

# 🙏 **Credits & Thanks**

Built with incredible open-source tools — thanks to the teams behind [FastAPI](https://fastapi.tiangolo.com/), [TanStack](https://tanstack.com/), [Capacitor](https://capacitorjs.com/), [NATS](https://nats.io/), and [Stripe](https://stripe.com/) for making a project like this possible.

---

# 📄 **License**

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

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
