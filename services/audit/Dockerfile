FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./
COPY services/audit/pyproject.toml services/audit/pyproject.toml
COPY packages/broker/pyproject.toml packages/broker/pyproject.toml
COPY packages/contracts/pyproject.toml packages/contracts/pyproject.toml
COPY packages/db/pyproject.toml packages/db/pyproject.toml
COPY packages/observability/pyproject.toml packages/observability/pyproject.toml
COPY uv.lock ./

RUN uv sync --package audit --no-dev --frozen

FROM python:3.12-slim AS runtime

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

COPY services/audit/src/ ./src/
COPY packages/broker/src/ ./src/
COPY packages/contracts/src/ ./src/
COPY packages/db/src/ ./src/
COPY packages/observability/src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8007

CMD ["python", "-m", "com.qode.qrew.v1.audit"]
