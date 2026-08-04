# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY packages/gie-contracts /app/packages/gie-contracts
COPY agents/chief-orchestrator /app/agents/chief-orchestrator
COPY frontend/command-console /app/frontend/command-console
COPY deploy/full-gie /workspace/deploy/full-gie

RUN pip install --upgrade pip && \
    pip install /app/packages/gie-contracts && \
    pip install /app/agents/chief-orchestrator

ENV PYTHONPATH=/app/agents/chief-orchestrator/src \
    ORCH_MULTI_REGION_CONFIG=/workspace/deploy/full-gie/multi-region.yaml \
    ORCH_CONSOLE_DIR=/app/frontend/command-console

EXPOSE 8090

HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/healthz')" || exit 1

CMD ["uvicorn", "chief_orchestrator.app:app", "--host", "0.0.0.0", "--port", "8090"]
