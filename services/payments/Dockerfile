FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./
COPY services/payments/pyproject.toml services/payments/pyproject.toml
COPY packages/common/pyproject.toml packages/common/pyproject.toml
COPY uv.lock ./

RUN uv sync --package payments --no-dev --frozen

FROM python:3.12-slim AS runtime

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

COPY services/payments/src/ ./src/
COPY packages/common/src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8002

CMD ["python", "-m", "com.qode.qrew.v1.payments"]
