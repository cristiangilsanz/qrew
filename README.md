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

> [!WARNING]
> This is a picture of the system. The full dive into the topic is in [OVERVIEW.md](docs/architecture/overview.md).

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

<div align="right">

→ [Full Architecture View](docs/architecture/overview.md)

</div>

</div>

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
- 📲 [Android · USB](docs/development/setup/android-usb.md)
- 📱 [Android · Emulator](docs/development/setup/android-emulator.md)

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

| Secret |
|---|
| `access_jwt_private_key` |
| `pii_encryption_key` |
| `stripe_secret_key` |
| `stripe_webhook_signing_secret` |
| `twilio_account_sid` / `twilio_auth_token` |
| `captcha_secret_key` |
| `storage_signing_key` |

> [!NOTE]
> Most secrets can be left empty for local dev. Features that need them are disabled by default via their `*_enabled: false` flags.

**4. Spin up the full stack**

```bash
docker compose up
```


# 📚 **Tech Stack**

## 🗣️ Languages

[![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=for-the-badge&logo=python&logoColor=fff)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript_5-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)

## 🧩 Frameworks & Libraries

[![React](https://img.shields.io/badge/React_19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite_6-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Uvicorn](https://img.shields.io/badge/Uvicorn-499848?style=for-the-badge&logo=gunicorn&logoColor=white)](https://www.uvicorn.org/)
[![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-CC2927?style=for-the-badge&logo=postgresql&logoColor=white)](https://docs.sqlalchemy.org/)
[![Alembic](https://img.shields.io/badge/Alembic-6BA539?style=for-the-badge&logo=postgresql&logoColor=white)](https://alembic.sqlalchemy.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS_4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![TanStack Router](https://img.shields.io/badge/TanStack_Router-FF4154?style=for-the-badge&logo=reactrouter&logoColor=white)](https://tanstack.com/router)
[![TanStack Query](https://img.shields.io/badge/TanStack_Query-FF4154?style=for-the-badge&logo=reactquery&logoColor=white)](https://tanstack.com/query)
[![Zustand](https://img.shields.io/badge/Zustand-443E38?style=for-the-badge&logo=react&logoColor=white)](https://zustand-demo.pmnd.rs/)
[![Immer](https://img.shields.io/badge/Immer-00E7C3?style=for-the-badge&logo=javascript&logoColor=black)](https://immerjs.github.io/immer/)
[![Capacitor](https://img.shields.io/badge/Capacitor-119EFF?style=for-the-badge&logo=capacitor&logoColor=white)](https://capacitorjs.com/)
[![Radix UI](https://img.shields.io/badge/Radix_UI-161618?style=for-the-badge&logo=radixui&logoColor=white)](https://www.radix-ui.com/)
[![Framer Motion](https://img.shields.io/badge/Framer_Motion-0055FF?style=for-the-badge&logo=framer&logoColor=white)](https://www.framer.com/motion/)
[![React Hook Form](https://img.shields.io/badge/React_Hook_Form-EC5990?style=for-the-badge&logo=reacthookform&logoColor=white)](https://react-hook-form.com/)
[![Zod](https://img.shields.io/badge/Zod-3068B7?style=for-the-badge&logo=typescript&logoColor=white)](https://zod.dev/)
[![Axios](https://img.shields.io/badge/Axios-671DDF?style=for-the-badge&logo=axios&logoColor=white)](https://axios-http.com/)
[![react-i18next](https://img.shields.io/badge/react--i18next-26A69A?style=for-the-badge&logo=react&logoColor=white)](https://react.i18next.com/)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-000000?style=for-the-badge&logo=opentelemetry&logoColor=white)](https://opentelemetry.io/)
[![Structlog](https://img.shields.io/badge/Structlog-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.structlog.org/)
[![slowapi](https://img.shields.io/badge/slowapi-FF4500?style=for-the-badge&logo=fastapi&logoColor=white)](https://slowapi.readthedocs.io/)
[![httpx](https://img.shields.io/badge/httpx-1C2833?style=for-the-badge&logo=python&logoColor=white)](https://www.python-httpx.org/)
[![geoip2](https://img.shields.io/badge/geoip2-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://geoip2.readthedocs.io/)
[![pytesseract](https://img.shields.io/badge/pytesseract-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://github.com/madmaze/pytesseract)
[![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org/)
[![Pillow](https://img.shields.io/badge/Pillow-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://pillow.readthedocs.io/)
[![Stripe Elements](https://img.shields.io/badge/Stripe_Elements-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://stripe.com/docs/stripe-js)
[![stripe SDK](https://img.shields.io/badge/stripe_SDK-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://github.com/stripe/stripe-python)
[![Lucide React](https://img.shields.io/badge/Lucide_React-F56565?style=for-the-badge&logo=react&logoColor=white)](https://lucide.dev/)
[![Sonner](https://img.shields.io/badge/Sonner-000000?style=for-the-badge&logo=react&logoColor=white)](https://sonner.emilkowal.ski/)
[![date-fns](https://img.shields.io/badge/date--fns-770C56?style=for-the-badge&logo=javascript&logoColor=white)](https://date-fns.org/)
[![react-qr-code](https://img.shields.io/badge/react--qr--code-000000?style=for-the-badge&logo=react&logoColor=white)](https://github.com/rosskhanas/react-qr-code)

## 🗄️ Databases

[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-FF4438?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![asyncpg](https://img.shields.io/badge/asyncpg-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/MagicStack/asyncpg)

## 🐳 Infrastructure

[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Docker Compose](https://img.shields.io/badge/Docker_Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Jaeger](https://img.shields.io/badge/Jaeger-66CFE3?style=for-the-badge&logo=opentelemetry&logoColor=black)](https://www.jaegertracing.io/)

## ⚡ Messaging & Background Jobs

[![NATS JetStream](https://img.shields.io/badge/NATS_JetStream-27AAE1?style=for-the-badge&logo=rabbitmq&logoColor=white)](https://docs.nats.io/nats-concepts/jetstream)
[![nats-py](https://img.shields.io/badge/nats--py-27AAE1?style=for-the-badge&logo=rabbitmq&logoColor=white)](https://github.com/nats-io/nats.py)
[![Arq](https://img.shields.io/badge/Arq-0099CC?style=for-the-badge&logo=redis&logoColor=white)](https://arq-docs.helpmanual.io/)
[![Redlock](https://img.shields.io/badge/Redlock-FF4438?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/docs/latest/develop/use/patterns/distributed-locks/)

## 🔐 Security & Auth

[![cryptography](https://img.shields.io/badge/cryptography-2C3E50?style=for-the-badge&logo=openssl&logoColor=white)](https://cryptography.io/)
[![Passlib](https://img.shields.io/badge/Passlib-1C2833?style=for-the-badge&logo=python&logoColor=white)](https://passlib.readthedocs.io/)
[![argon2-cffi](https://img.shields.io/badge/argon2--cffi-1C2833?style=for-the-badge&logo=python&logoColor=white)](https://argon2-cffi.readthedocs.io/)
[![PyJWT](https://img.shields.io/badge/PyJWT-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://pyjwt.readthedocs.io/)
[![WebAuthn](https://img.shields.io/badge/WebAuthn-1D232A?style=for-the-badge&logo=1password&logoColor=white)](https://webauthn.io/)
[![SimpleWebAuthn](https://img.shields.io/badge/SimpleWebAuthn-4A6B8A?style=for-the-badge&logo=javascript&logoColor=white)](https://simplewebauthn.dev/)
[![pyotp](https://img.shields.io/badge/pyotp-1C2833?style=for-the-badge&logo=python&logoColor=white)](https://pyauth.github.io/pyotp/)

## 💳 Third-Party Services

[![Stripe](https://img.shields.io/badge/Stripe-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://stripe.com/docs)
[![Twilio](https://img.shields.io/badge/Twilio-F22F46?style=for-the-badge&logo=twilio&logoColor=white)](https://www.twilio.com/docs)
[![Google Maps](https://img.shields.io/badge/Google_Maps-4285F4?style=for-the-badge&logo=googlemaps&logoColor=white)](https://developers.google.com/maps)
[![Cloudflare Turnstile](https://img.shields.io/badge/Cloudflare_Turnstile-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)](https://developers.cloudflare.com/turnstile/)
[![HIBP](https://img.shields.io/badge/HIBP-2E6DA4?style=for-the-badge&logo=haveibeenpwned&logoColor=white)](https://haveibeenpwned.com/API/v3)

## 🧪 Testing

[![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Vitest](https://img.shields.io/badge/Vitest-6E9F18?style=for-the-badge&logo=vitest&logoColor=white)](https://vitest.dev/)
[![React Testing Library](https://img.shields.io/badge/React_Testing_Library-E33332?style=for-the-badge&logo=testinglibrary&logoColor=white)](https://testing-library.com/)
[![Testcontainers](https://img.shields.io/badge/Testcontainers-291A3F?style=for-the-badge&logo=docker&logoColor=white)](https://testcontainers.com/)
[![fakeredis](https://img.shields.io/badge/fakeredis-FF4438?style=for-the-badge&logo=redis&logoColor=white)](https://github.com/cunla/fakeredis-py)
[![MSW](https://img.shields.io/badge/MSW-FF6A33?style=for-the-badge&logo=javascript&logoColor=white)](https://mswjs.io/)
[![factory-boy](https://img.shields.io/badge/factory--boy-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://factoryboy.readthedocs.io/)

## 🔍 Code Quality

[![Pyright](https://img.shields.io/badge/Pyright-0078D4?style=for-the-badge&logo=visualstudiocode&logoColor=white)](https://github.com/microsoft/pyright)
[![ESLint](https://img.shields.io/badge/ESLint-4B32C3?style=for-the-badge&logo=eslint&logoColor=white)](https://eslint.org/)
[![Ruff](https://img.shields.io/badge/Ruff-D7FF64?style=for-the-badge&logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![Prettier](https://img.shields.io/badge/Prettier-F7B93E?style=for-the-badge&logo=prettier&logoColor=black)](https://prettier.io/)

## 🔧 Tooling

[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](https://docs.github.com/en/actions)
[![just](https://img.shields.io/badge/just-A52A2A?style=for-the-badge&logo=gnubash&logoColor=white)](https://just.systems/)
[![uv](https://img.shields.io/badge/uv-DE5FE9?style=for-the-badge&logo=python&logoColor=white)](https://docs.astral.sh/uv/)
[![Husky](https://img.shields.io/badge/Husky-1C3148?style=for-the-badge&logo=git&logoColor=white)](https://typicode.github.io/husky/)
[![lint-staged](https://img.shields.io/badge/lint--staged-ECB22E?style=for-the-badge&logo=git&logoColor=black)](https://github.com/lint-staged/lint-staged)
[![commitlint](https://img.shields.io/badge/commitlint-000000?style=for-the-badge&logo=conventionalcommits&logoColor=white)](https://commitlint.js.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-FAB040?style=for-the-badge&logo=precommit&logoColor=black)](https://pre-commit.com/)

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
