FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.10.12 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./
COPY apps/api/gateway/pyproject.toml apps/api/gateway/pyproject.toml
COPY packages/shared-python/exceptions/pyproject.toml packages/shared-python/exceptions/pyproject.toml
COPY packages/shared-python/idempotency/pyproject.toml packages/shared-python/idempotency/pyproject.toml
COPY packages/shared-python/middleware/pyproject.toml packages/shared-python/middleware/pyproject.toml
COPY packages/shared-python/security/pyproject.toml packages/shared-python/security/pyproject.toml
COPY packages/shared-python/observability/pyproject.toml packages/shared-python/observability/pyproject.toml
COPY packages/contracts/pyproject.toml packages/contracts/pyproject.toml
COPY uv.lock ./

RUN uv sync --package gateway --no-dev --frozen

FROM python:3.12-slim AS runtime

RUN useradd --system --no-create-home --uid 1001 appuser

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

COPY apps/api/gateway/src/ ./src/
COPY packages/shared-python/exceptions/src/ ./src/
COPY packages/shared-python/idempotency/src/ ./src/
COPY packages/shared-python/middleware/src/ ./src/
COPY packages/shared-python/security/src/ ./src/
COPY packages/shared-python/observability/src/ ./src/
COPY packages/contracts/src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOST="0.0.0.0"

USER appuser

EXPOSE 8008

CMD ["python", "-m", "com.qode.qrew.v1.gateway"]
