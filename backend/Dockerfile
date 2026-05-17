# syntax=docker/dockerfile:1
# Shared image for API, LiveKit agent worker, and Celery.
ARG PYTHON_VERSION=3.11.9
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/app" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    appuser

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cache model weights under /app so the non-root runtime user can read them.
ENV HF_HOME=/app/.cache/huggingface \
    XDG_CACHE_HOME=/app/.cache

RUN mkdir -p /app/.cache && chown -R appuser:appuser /app

USER appuser

# livekit.agents has no __main__; download via registered plugins (see download_agent_assets.py).
RUN python download_agent_assets.py

ENV CLEAN_DATABASE_ON_EXIT=false

# Override per service on Northflank (api / agent / celery).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
