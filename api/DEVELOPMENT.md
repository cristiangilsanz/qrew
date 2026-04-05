
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
> **Install pre-requisites:**
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

> [!TIP]
> **Configure pre-commit hooks:**
> ```bash
> cd api && uv run pre-commit install
> ```
---

## 🔐 Environment Variables

>[!NOTE]
> **This is an optional step!**
>
> The app will run using the default values in `settings.py`.

You can override them by creating a local `.env` file. To do this, copy the example file and edit it as needed:

```bash
cp api/.env.example api/.env
```

