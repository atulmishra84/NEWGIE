# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/pyproject.toml
COPY packages/gie-contracts /app/packages/gie-contracts
COPY packages/gie-observability /app/packages/gie-observability
COPY packages/gie-security /app/packages/gie-security
COPY agents/context-intelligence /app/agents/context-intelligence

RUN pip install --upgrade pip && \
    pip install /app/packages/gie-contracts /app/packages/gie-observability /app/packages/gie-security && \
    pip install /app/agents/context-intelligence

ENV PYTHONPATH=/app/agents/context-intelligence/src

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')" || exit 1

CMD ["uvicorn", "context_intelligence.adapters.rest.app:app", "--host", "0.0.0.0", "--port", "8080"]
