# Prerequisites

## Introduction

The following tools are required to run the development stack, so install all required entries before proceeding to the setup guides:

| Tool | | Version | Required |
|---|---|---|---|
| [Docker Desktop](#docker-desktop) | ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white) | Latest | ✅ |
| [Node.js 20](#nodejs-20) | ![Node.js](https://img.shields.io/badge/Node.js-339933?style=flat&logo=nodedotjs&logoColor=white) | 20 | ✅ |
| [Python 3.12](#python-312) | ![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white) | 3.12 | ✅ |
| [uv](#uv) | ![uv](https://img.shields.io/badge/uv-DE5FE9?style=flat&logo=astral&logoColor=white) | Latest | ✅ |
| [just](#just) | ![just](https://img.shields.io/badge/just-1a1a1a?style=flat&logo=gnubash&logoColor=white) | Latest | ✅ |
| [Android Studio](#android-studio-mobile-only) | ![Android Studio](https://img.shields.io/badge/Android_Studio-3DDC84?style=flat&logo=androidstudio&logoColor=white) | Latest | Mobile only |
| [Java 17](#java-17-mobile-only) | ![Java](https://img.shields.io/badge/Java-ED8B00?style=flat&logo=openjdk&logoColor=white) | 17 | Mobile only |
| [Xcode](#xcode-ios-only) | ![Xcode](https://img.shields.io/badge/Xcode-147EFB?style=flat&logo=xcode&logoColor=white) | Latest | iOS only |
| [Stripe CLI](#stripe-cli-optional) | ![Stripe](https://img.shields.io/badge/Stripe-635BFF?style=flat&logo=stripe&logoColor=white) | Latest | Optional |
| [cloudflared](#cloudflared-optional) | ![Cloudflare](https://img.shields.io/badge/cloudflared-F38020?style=flat&logo=cloudflare&logoColor=white) | Latest | Optional |

## Version Managers *(Recommended)*

For managing multiple versions of Node.js and Python across projects, you can install a version manager before running the steps below.

### nvm

Manages Node.js versions. Required before installing Node.js 20.

To install on macOS / Linux:
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash
```

To verify:
```bash
nvm --version
# 0.x.x
```

<div align="right"><a href="https://github.com/nvm-sh/nvm">Visit the official website here →</a></div>

### pyenv

Manages Python versions. Required before installing Python 3.12.

To install on macOS:
```bash
brew install pyenv
```

To install on Linux:
```bash
curl https://pyenv.run | bash
```

To verify:
```bash
pyenv --version
# pyenv x.x.x
```

<div align="right"><a href="https://github.com/pyenv/pyenv">Visit the official website here →</a></div>

## Installation Guides

### Docker Desktop

To install on macOS:
```bash
brew install --cask docker
```

To install on Linux:
```bash
sudo apt-get install docker-ce docker-compose-plugin
```

To verify:
```bash
docker --version && docker compose version
# Docker version 26.x.x
# Docker Compose version v2.x.x
```

<div align="right"><a href="https://www.docker.com/products/docker-desktop">Visit the official website here →</a></div>

### Node.js 20

Use [nvm](https://github.com/nvm-sh/nvm) to manage versions.

To install on macOS / Linux:
```bash
nvm install 20
nvm use 20
```

To verify:
```bash
node --version && npm --version
# v20.x.x
# 10.x.x
```

<div align="right"><a href="https://nodejs.org">Visit the official website here →</a></div>

### Python 3.12

Use [pyenv](https://github.com/pyenv/pyenv) to manage versions.

To install on macOS / Linux:
```bash
pyenv install 3.12
pyenv global 3.12
```

To verify:
```bash
python3 --version
# Python 3.12.x
```

<div align="right"><a href="https://www.python.org">Visit the official website here →</a></div>

### uv

To install on macOS / Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

To verify:
```bash
uv --version
# uv 0.x.x
```

<div align="right"><a href="https://docs.astral.sh/uv">Visit the official website here →</a></div>

### just

To install on macOS:
```bash
brew install just
```

To install on Linux:
```bash
cargo install just
```

To verify:
```bash
just --version
# just 1.x.x
```

<div align="right"><a href="https://just.systems">Visit the official website here →</a></div>

### Android Studio *(Mobile only)*

To install on macOS:
```bash
brew install --cask android-studio
```

To install on Linux: download from the link above.

<div align="right"><a href="https://developer.android.com/studio">Visit the official website here →</a></div>

### Java 17 *(Mobile only)*

Use [SDKMAN](https://sdkman.io) or a package manager.

To install on macOS:
```bash
brew install openjdk@17
```

To install on Linux:
```bash
sudo apt-get install openjdk-17-jdk
```

To verify:
```bash
java --version
# openjdk 17.x.x
```

<div align="right"><a href="https://openjdk.org">Visit the official website here →</a></div>

### Xcode *(iOS only)*

macOS only, install from the App Store.

<div align="right"><a href="https://apps.apple.com/app/xcode/id497799835">Visit the official website here →</a></div>

### Stripe CLI *(Optional)*

Required only to test Stripe webhooks locally via `just stripe-dev`. Forwards webhook events to the local payments service.

To install on macOS:
```bash
brew install stripe/stripe-cli/stripe
```

To install on Linux:
```bash
curl -s https://packages.stripe.dev/api/security/keypair/stripe-cli-gpg/public | gpg --dearmor | sudo tee /usr/share/keyrings/stripe.gpg
echo "deb [signed-by=/usr/share/keyrings/stripe.gpg] https://packages.stripe.dev/stripe-cli-debian-local stable main" | sudo tee /etc/apt/sources.list.d/stripe.list
sudo apt update && sudo apt install stripe
```

To verify:
```bash
stripe --version
# stripe version x.x.x
```

<div align="right"><a href="https://stripe.com/docs/stripe-cli">Visit the official website here →</a></div>

### cloudflared *(Optional)*

Required only to run `npm run dev:tunnel`, which opens a named Cloudflare tunnel at `https://qrew-dev.uk` for testing on physical devices.

To install on macOS:
```bash
brew install cloudflare/cloudflare/cloudflared
```

To install on Linux:
```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o ~/.local/bin/cloudflared
chmod +x ~/.local/bin/cloudflared
```

To verify:
```bash
cloudflared --version
# cloudflared version x.x.x
```

<div align="right"><a href="https://developers.cloudflare.com/cloudflared">Visit the official website here →</a></div>
