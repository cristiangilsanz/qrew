FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./
COPY services/sales/pyproject.toml services/sales/pyproject.toml
COPY packages/audit-publisher/pyproject.toml packages/audit-publisher/pyproject.toml
COPY packages/broker/pyproject.toml packages/broker/pyproject.toml
COPY packages/contracts/pyproject.toml packages/contracts/pyproject.toml
COPY packages/db/pyproject.toml packages/db/pyproject.toml
COPY packages/http-errors/pyproject.toml packages/http-errors/pyproject.toml
COPY packages/idempotency/pyproject.toml packages/idempotency/pyproject.toml
COPY packages/jobs/pyproject.toml packages/jobs/pyproject.toml
COPY packages/locking/pyproject.toml packages/locking/pyproject.toml
COPY packages/middleware/pyproject.toml packages/middleware/pyproject.toml
COPY packages/observability/pyproject.toml packages/observability/pyproject.toml
COPY packages/pagination/pyproject.toml packages/pagination/pyproject.toml
COPY packages/probes/pyproject.toml packages/probes/pyproject.toml
COPY packages/ratelimit/pyproject.toml packages/ratelimit/pyproject.toml
COPY packages/security/pyproject.toml packages/security/pyproject.toml
COPY packages/worker/pyproject.toml packages/worker/pyproject.toml
COPY uv.lock ./

RUN uv sync --package sales --no-dev --frozen

FROM python:3.12-slim AS runtime

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

COPY services/sales/src/ ./src/
COPY packages/broker/src/ ./src/
COPY packages/contracts/src/ ./src/
COPY packages/db/src/ ./src/
COPY packages/http-errors/src/ ./src/
COPY packages/idempotency/src/ ./src/
COPY packages/locking/src/ ./src/
COPY packages/middleware/src/ ./src/
COPY packages/observability/src/ ./src/
COPY packages/probes/src/ ./src/
COPY packages/worker/src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8005

CMD ["python", "-m", "com.qode.qrew.v1.sales"]
