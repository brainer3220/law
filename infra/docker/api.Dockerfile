# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.11-bookworm AS builder
WORKDIR /app

ENV UV_CACHE_DIR=/root/.cache/uv

COPY apps/api/pyproject.toml apps/api/uv.lock ./apps/api/
COPY packages/py-shared/ ./packages/py-shared/

RUN --mount=type=cache,target=/root/.cache/uv \
    cd apps/api && uv sync --no-dev

FROM python:3.11-slim AS runtime
WORKDIR /app/apps/api

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/apps/api/.venv /app/apps/api/.venv

COPY apps/api/ /app/apps/api/
COPY packages/py-shared/ /app/packages/py-shared/

ENV PATH="/app/apps/api/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
