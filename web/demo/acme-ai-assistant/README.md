# ACME AI Assistant — sample target for GIE sandbox E2E demos
# Analyze with: tenant=acme, source.path=/demo/acme-ai-assistant

name: acme-ai-assistant
description: Customer-support RAG chatbot on Azure OpenAI
runtime: python3.12
framework: fastapi
model:
  provider: azure-openai
  name: gpt-4o-mini
  deployment: acme-chat-mini
data_stores:
  - postgres (chat_history, 90d retention)
  - qdrant (acme-docs)
ingress:
  - public HTTPS /v1/chat
risks_hint:
  - prompt_injection
  - pii_in_logs
  - no_model_change_gate
