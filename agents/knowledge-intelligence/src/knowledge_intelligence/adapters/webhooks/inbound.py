"""Inbound webhook for knowledge corpus updates."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from gie_contracts.knowledge import KnowledgeUpsertRequest

from knowledge_intelligence.application.di import get_container

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


@router.post("/knowledge/ingest")
async def ingest_webhook(
    body: KnowledgeUpsertRequest,
    x_webhook_secret: str | None = Header(default=None),
):
    # Secret comparison would use settings in production
    if x_webhook_secret is None:
        raise HTTPException(status_code=401, detail="missing webhook secret")
    container = get_container()
    result = await container.upsert.handle(
        body,
        tenant_id="webhook",
        actor="webhook",
        correlation_id="webhook",
    )
    return result
