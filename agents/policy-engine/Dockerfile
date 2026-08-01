# syntax=docker/dockerfile:1
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY packages/gie-contracts /app/packages/gie-contracts
COPY agents/policy-engine /app/agents/policy-engine
RUN pip install --upgrade pip && \
    pip install /app/packages/gie-contracts && \
    pip install /app/agents/policy-engine
ENV PYTHONPATH=/app/agents/policy-engine/src
EXPOSE 8092
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8092/healthz')" || exit 1
CMD ["uvicorn", "policy_engine.app:app", "--host", "0.0.0.0", "--port", "8092"]
