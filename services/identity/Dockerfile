FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./
COPY services/identity/pyproject.toml services/identity/pyproject.toml
COPY packages/broker/pyproject.toml packages/broker/pyproject.toml
COPY packages/contracts/pyproject.toml packages/contracts/pyproject.toml
COPY packages/db/pyproject.toml packages/db/pyproject.toml
COPY packages/locking/pyproject.toml packages/locking/pyproject.toml
COPY packages/middleware/pyproject.toml packages/middleware/pyproject.toml
COPY packages/observability/pyproject.toml packages/observability/pyproject.toml
COPY packages/pagination/pyproject.toml packages/pagination/pyproject.toml
COPY packages/idempotency/pyproject.toml packages/idempotency/pyproject.toml
COPY packages/jobs/pyproject.toml packages/jobs/pyproject.toml
COPY packages/security/pyproject.toml packages/security/pyproject.toml
COPY packages/ratelimit/pyproject.toml packages/ratelimit/pyproject.toml
COPY uv.lock ./

RUN uv sync --package identity --no-dev --frozen

FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

COPY services/identity/src/ ./src/
COPY packages/broker/src/ ./src/
COPY packages/contracts/src/ ./src/
COPY packages/db/src/ ./src/
COPY packages/locking/src/ ./src/
COPY packages/middleware/src/ ./src/
COPY packages/observability/src/ ./src/
COPY packages/pagination/src/ ./src/
COPY packages/idempotency/src/ ./src/
COPY packages/jobs/src/ ./src/
COPY packages/security/src/ ./src/
COPY packages/ratelimit/src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8006

CMD ["python", "-m", "com.qode.qrew.v1.identity"]
