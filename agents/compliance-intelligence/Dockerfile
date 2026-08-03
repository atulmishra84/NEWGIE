FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
COPY packages/gie-contracts /packages/gie-contracts
COPY packages/gie-observability /packages/gie-observability
COPY packages/gie-security /packages/gie-security
COPY agents/compliance-intelligence /app
RUN pip install --upgrade pip \
 && pip install /packages/gie-contracts /packages/gie-observability /packages/gie-security \
 && pip install -e .
ENV GIE_ENV=prod
ENV GIE_COMPLIANCE_CATALOG_PATH=/app/data/frameworks/catalog_v1.json
EXPOSE 8084
CMD ["uvicorn", "compliance_intelligence.adapters.rest.app:app", "--host", "0.0.0.0", "--port", "8084"]
