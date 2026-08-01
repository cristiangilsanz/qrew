# Prerequisites

Everything you need installed before running QREW locally.


## Required tools

| Tool | Minimum version | Purpose |
|---|---|---|
| Docker Desktop | Latest stable | PostgreSQL, Redis, NATS containers |
| Docker Compose | v2 | Multi-container orchestration |
| Node.js | 20 | Frontend dev server and build |
| npm | 10 | Frontend package management |
| Python | 3.12 | Backend services |
| uv | Latest | Python package and venv management |
| just | Latest | Task runner |
| git | Any | Version control |


## Installation

### Docker Desktop

Download and install from the Docker website. On Linux, install the Docker Engine and the Compose plugin separately.

Verify:

```bash
docker --version
docker compose version
```

### Node.js

Use the official installer or a version manager such as `nvm`:

```bash
nvm install 20
nvm use 20
```

### Python 3.12

Download from the Python website or use `pyenv`:

```bash
pyenv install 3.12
pyenv global 3.12
```

### uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart your terminal after installation. Verify with `uv --version`.

### just

macOS:

```bash
brew install just
```

Linux or Windows:

```bash
cargo install just
# or download a binary from https://just.systems/
```


## Mobile development (optional)

Only needed if you plan to build or test the Android or iOS app. See [EMULATOR.md](EMULATOR.md) or [DEVICE.md](DEVICE.md).

| Tool | Purpose |
|---|---|
| Android Studio | Android SDK, emulator |
| Xcode (macOS only) | iOS SDK, simulator |
| Java 17 | Gradle build system |


## Optional tools

| Tool | Purpose |
|---|---|
| Stripe CLI | Forward Stripe webhooks to local payments service |
| `jq` | Pretty-print API responses in the terminal |
| Jaeger | View distributed traces from OpenTelemetry |

Stripe CLI install:

```bash
brew install stripe/stripe-cli/stripe
# or see https://stripe.com/docs/stripe-cli
```


## Checking versions

Run this to verify your setup at any time:

```bash
docker --version
docker compose version
node --version
npm --version
python3 --version
uv --version
just --version
```
