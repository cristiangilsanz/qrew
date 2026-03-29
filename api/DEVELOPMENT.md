
# ⚙️ Qrew API — Development Local Setup Guide

Get from zero to a running local environment as quickly as possible.

## 📋 Prerequisites

Make sure you have the following installed before starting:

| Tool | Version |
| :--- | :------ |
| [Python](https://www.python.org/downloads/) | `3.12+` |
| [UV](https://docs.astral.sh/uv/getting-started/installation/) | `latest` |
| [Just](https://github.com/casey/just#installation) | `latest` |
| [Docker](https://docs.docker.com/get-docker/) | `24+` |
| [Docker Compose](https://docs.docker.com/compose/install/) | `v2+` |

> [!TIP]
> **Install prerequisites:**
> ```bash
> sudo apt update && sudo apt install -y python3.12 docker.io docker-compose-v2
> curl -LsSf https://astral.sh/uv/install.sh | sh
> curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin
> ```

---

## 💻 Installation

Follow these steps in order:

### 1️⃣ Bootstrap

```bash
just setup
```

### 2️⃣ Apply DB migrations

```bash
just db-upgrade
```

### 3️⃣ Run the API

```bash
just dev
```

[!IMPORTANT]
> **Configure pre-commit hooks:**
> ```bash
> cd api && uv run pre-commit install
> ```
---

## 🔐 Environment Variables

Copy the example file and edit it:

```bash
cp api/.env.example api/.env
```

> [!NOTE]
> All variables below have defaults that work out of the box with the Docker Compose local setup.

| Variable | Default |
| :------- | :------ |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:sekret@localhost:5432/qrew` |
| `SECRET_KEY` | `dev-secret-key-change-in-production` |
| `ENVIRONMENT` | `development` |
| `DEBUG` | `true` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `CORS_ORIGINS` | `["http://localhost:3000"]` |
| `HOST` | `127.0.0.1` |
| `PORT` | `8000` |

### 🔑 Generate a secure `SECRET_KEY`

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> [!CAUTION]
> **Never** use the default `SECRET_KEY` in PROD.
