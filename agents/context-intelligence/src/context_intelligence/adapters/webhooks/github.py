"""Inbound GitHub push webhook handler."""

from __future__ import annotations

import hashlib
import hmac
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request, status
from gie_contracts.sources import GitHubSource

from context_intelligence.adapters.rest.deps import get_event_publisher
from context_intelligence.domain.scan_executor import request_scan
from context_intelligence.infrastructure.celery_app import execute_scan_task
from context_intelligence.infrastructure.persistence.database import session_scope
from context_intelligence.infrastructure.persistence.repositories import (
    SqlAlchemyContextRepository,
    SqlAlchemyOutboxWriter,
)
from context_intelligence.settings import get_settings

router = APIRouter(prefix="/webhooks/github", tags=["webhooks"])


def _verify_signature(body: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


@router.post("/push")
async def github_push(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    x_github_event: str | None = Header(default=None, alias="X-GitHub-Event"),
) -> dict[str, str]:
    settings = get_settings()
    body = await request.body()
    if settings.github_webhook_secret:
        if not _verify_signature(
            body, x_hub_signature_256, settings.github_webhook_secret
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature"
            )

    if x_github_event != "push":
        return {"status": "ignored", "reason": "not_a_push_event"}

    payload = await request.json()
    repo = payload.get("repository") or {}
    owner = (repo.get("owner") or {}).get("login") or repo.get("full_name", "").split(
        "/"
    )[0]
    name = repo.get("name")
    ref = (payload.get("ref") or "refs/heads/main").replace("refs/heads/", "")
    if not owner or not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing repository info",
        )

    tenant_id = request.headers.get("X-Tenant-ID") or "github-webhook"
    source = GitHubSource(owner=owner, repo=name, ref=ref)
    correlation_id = request.headers.get("X-Correlation-ID") or uuid4().hex
    publisher = get_event_publisher()

    async with session_scope() as session:
        repo_impl = SqlAlchemyContextRepository(session)
        outbox = SqlAlchemyOutboxWriter(session)
        record = await request_scan(
            repo_impl,
            outbox,
            publisher,
            tenant_id=tenant_id,
            source=source,
            requested_by=f"github:{owner}/{name}",
            idempotency_key=f"github:{payload.get('after', uuid4().hex)}",
            correlation_id=correlation_id,
        )
    execute_scan_task.delay(record["scan_id"], tenant_id, correlation_id)
    return {"status": "accepted", "scan_id": record["scan_id"]}
