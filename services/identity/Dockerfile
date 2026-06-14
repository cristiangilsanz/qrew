FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./
COPY services/identity/pyproject.toml services/identity/pyproject.toml
COPY packages/common/pyproject.toml packages/common/pyproject.toml
COPY uv.lock ./

RUN uv sync --package identity --no-dev --frozen

FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

COPY services/identity/src/ ./src/
COPY packages/common/src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8006

CMD ["python", "-m", "com.qode.qrew.v1.identity"]
