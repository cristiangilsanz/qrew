FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./
COPY services/identity/pyproject.toml services/identity/pyproject.toml
COPY packages/shared-python/exceptions/pyproject.toml packages/shared-python/exceptions/pyproject.toml
COPY packages/shared-python/idempotency/pyproject.toml packages/shared-python/idempotency/pyproject.toml
COPY packages/shared-python/middleware/pyproject.toml packages/shared-python/middleware/pyproject.toml
COPY packages/shared-python/ratelimit/pyproject.toml packages/shared-python/ratelimit/pyproject.toml
COPY packages/shared-python/observability/pyproject.toml packages/shared-python/observability/pyproject.toml
COPY packages/shared-python/db/pyproject.toml packages/shared-python/db/pyproject.toml
COPY packages/shared-python/jobs/pyproject.toml packages/shared-python/jobs/pyproject.toml
COPY packages/shared-python/locking/pyproject.toml packages/shared-python/locking/pyproject.toml
COPY packages/shared-python/messaging/pyproject.toml packages/shared-python/messaging/pyproject.toml
COPY packages/shared-python/worker/pyproject.toml packages/shared-python/worker/pyproject.toml
COPY packages/shared-python/pagination/pyproject.toml packages/shared-python/pagination/pyproject.toml
COPY packages/contracts/pyproject.toml packages/contracts/pyproject.toml
COPY uv.lock ./

RUN uv sync --package identity --no-dev --frozen

FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

COPY services/identity/src/ ./src/
COPY packages/shared-python/exceptions/src/ ./src/
COPY packages/shared-python/idempotency/src/ ./src/
COPY packages/shared-python/middleware/src/ ./src/
COPY packages/shared-python/ratelimit/src/ ./src/
COPY packages/shared-python/observability/src/ ./src/
COPY packages/shared-python/db/src/ ./src/
COPY packages/shared-python/jobs/src/ ./src/
COPY packages/shared-python/locking/src/ ./src/
COPY packages/shared-python/messaging/src/ ./src/
COPY packages/shared-python/worker/src/ ./src/
COPY packages/shared-python/pagination/src/ ./src/
COPY packages/contracts/src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8006

CMD ["python", "-m", "com.qode.qrew.v1.identity"]
