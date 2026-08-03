FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
COPY packages/gie-contracts /packages/gie-contracts
COPY packages/gie-observability /packages/gie-observability
COPY packages/gie-security /packages/gie-security
COPY agents/orchestrator /app
RUN pip install --upgrade pip \
 && pip install /packages/gie-contracts /packages/gie-observability /packages/gie-security \
 && pip install -e .
ENV GIE_ENV=prod
EXPOSE 8091
CMD ["uvicorn", "orchestrator.adapters.rest.app:app", "--host", "0.0.0.0", "--port", "8091"]
