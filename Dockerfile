# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

COPY . .
RUN mkdir -p /app/data

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

ENV PORT=8000
ENV NEXUS_DB_PATH=/app/data/nexus.db
EXPOSE 8000

CMD ["uv", "run", "python", "run.py"]
