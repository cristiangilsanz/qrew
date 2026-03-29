# ── Stage 1: Dependency Installation ─────────────────────────────────────────
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./

RUN uv sync --no-dev --frozen

# ── Stage 2: Runtime Image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "com.qode.qrew.v1.service.main:app", "--host", "0.0.0.0", "--port", "8000"]
