```
  ██████╗ ██████╗ ███████╗██╗    ██╗
 ██╔═══██╗██╔══██╗██╔════╝██║    ██║
 ██║   ██║██████╔╝█████╗  ██║ █╗ ██║
 ██║▄▄ ██║██╔══██╗██╔══╝  ██║███╗██║
 ╚██████╔╝██║  ██║███████╗╚███╔███╔╝
  ╚══▀▀═╝ ╚═╝  ╚═╝╚══════╝ ╚══╝╚══╝
```

<div align="center">

**Event ticketing, reinvented for mobile.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-microservices-009688?style=flat-square&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![Stripe](https://img.shields.io/badge/Stripe-payments-635BFF?style=flat-square&logo=stripe&logoColor=white)
![License](https://img.shields.io/badge/license-private-lightgrey?style=flat-square)

</div>

---

qrew is a production-grade event ticketing platform built as a native mobile app. Attendees buy and resell tickets. Organisers run events end to end. Entry staff scan QR codes at the gate. One product, three roles, zero friction.

---

## What makes it different

**Native mobile, one codebase.** React and Capacitor deliver a true native experience on Android and iOS, with hardware camera access for the built-in QR scanner.

**Secure by design.** Passkey and TOTP authentication, ES256 JWT signing, PII encrypted at rest with Fernet, and a gateway that validates every request before it reaches a service.

**Live market and waitlists.** When an event sells out, buyers join an automated waitlist. When a ticket is listed for resale, the next person in line gets it first.

**Event-driven microservices.** Seven independent services communicate over NATS JetStream. No shared databases, no synchronous service calls. Just clean domain boundaries and at least once event delivery.

---

## How it works

```mermaid
graph LR
    A([Mobile App<br/>React + Capacitor]) -->|HTTPS| B[API Gateway<br/>JWT validation]

    B --> C[Identity<br/>Auth · Passkeys · KYC]
    B --> D[Catalog<br/>Events · Venues · Orgs]
    B --> E[Sales<br/>Reservations · Market]
    B --> F[Entry<br/>Scanners · QR Scan]

    D <-->|Domain events| G{{NATS JetStream}}
    E <-->|Domain events| G
    F <-->|Domain events| G

    G --> H[Ticketing<br/>Tickets · QR tokens]
    G --> I[Payments<br/>Stripe]
    G --> J[Audit<br/>Immutable log]

    C --- K[(PostgreSQL + Redis)]
    D --- K
    E --- K
    H --- K
    I --- K
```

---

## Stack

| Layer | Technology |
|---|---|
| Mobile app | React 18, TanStack Router, TanStack Query, Tailwind CSS |
| Native runtime | Capacitor, Android, iOS |
| API gateway | Python, Starlette |
| Backend services | Python, FastAPI, SQLAlchemy, Alembic |
| Auth | JWT ES256, WebAuthn passkeys, TOTP, Argon2 |
| Messaging | NATS JetStream |
| Data | PostgreSQL 16, Redis |
| Payments | Stripe |
| Background jobs | Arq, Redlock |

---

## Documentation

| | |
|---|---|
| Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Getting started | [docs/development/](docs/development/) |
| App | [docs/app/](docs/app/) |
| API | [docs/api/](docs/api/) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security | [SECURITY.md](SECURITY.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |

---

*Private repository. All rights reserved.*
