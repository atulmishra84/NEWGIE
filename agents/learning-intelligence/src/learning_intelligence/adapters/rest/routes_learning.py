from __future__ import annotations
import time
from uuid import uuid4
from fastapi import APIRouter, Depends, Query
from gie_contracts.envelope import ObservabilityEnvelope, ResponseMeta
from gie_contracts.learning import (
    ApproveKnowledgeRequest,
    FeedbackRequest,
    LearnRequest,
)
from gie_security.auth import AuthPrincipal
from learning_intelligence.adapters.rest.deps import container_dep, require_perm
from learning_intelligence.application.di import Container
from learning_intelligence.domain.rbac import LearningPermission
from learning_intelligence.version import AGENT_NAME, AGENT_VERSION

router = APIRouter(prefix="/v1", tags=["learning"])
alias = APIRouter(tags=["learning-alias"])


def _meta(started: float, confidence=None, reasoning=None) -> ResponseMeta:
    return ResponseMeta(
        trace_id=uuid4().hex,
        request_id=uuid4().hex,
        correlation_id=uuid4().hex,
        execution_ms=(time.perf_counter() - started) * 1000,
        confidence=confidence,
        reasoning_path=reasoning or [],
        agent_version=AGENT_VERSION,
        agent_name=AGENT_NAME,
    )


@router.post("/feedback")
@alias.post("/feedback")
async def feedback(
    body: FeedbackRequest,
    principal: AuthPrincipal = Depends(require_perm(LearningPermission.LEARN_FEEDBACK)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.event.tenant_id:
        body.event.tenant_id = principal.tenant_id
    result = await container.feedback_handler.handle(
        body, actor=principal.subject_id, correlation_id=uuid4().hex
    )
    return ObservabilityEnvelope(data=result, meta=_meta(started))


@router.post("/learn")
@alias.post("/learn")
async def learn(
    body: LearnRequest,
    principal: AuthPrincipal = Depends(require_perm(LearningPermission.LEARN_RUN)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.bundle.tenant_id:
        body.bundle.tenant_id = principal.tenant_id
    report = await container.learn.handle(
        body, actor=principal.subject_id, correlation_id=uuid4().hex
    )
    return ObservabilityEnvelope(
        data=report, meta=_meta(started, report.confidence.score, report.reasoning_path)
    )


@router.get("/learning/history")
@alias.get("/learning/history")
async def learning_history(
    agent_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    principal: AuthPrincipal = Depends(require_perm(LearningPermission.LEARN_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    items = await container.reports.history(
        principal.tenant_id, agent_id=agent_id, limit=limit, offset=offset
    )
    return ObservabilityEnvelope(
        data={"items": items, "count": len(items)}, meta=_meta(started)
    )


@router.get("/knowledge/changes")
@alias.get("/knowledge/changes")
async def knowledge_changes(
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    principal: AuthPrincipal = Depends(require_perm(LearningPermission.LEARN_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    items = await container.knowledge.list(
        principal.tenant_id, status=status, limit=limit, offset=offset
    )
    return ObservabilityEnvelope(
        data={
            "items": items,
            "count": len(items),
            "requires_human_approval_count": sum(
                1
                for i in items
                if i.requires_human_approval and i.status.value == "proposed"
            ),
        },
        meta=_meta(started),
    )


@router.post("/knowledge/approve")
@alias.post("/knowledge/approve")
async def knowledge_approve(
    body: ApproveKnowledgeRequest,
    principal: AuthPrincipal = Depends(require_perm(LearningPermission.LEARN_APPROVE)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.tenant_id:
        body.tenant_id = principal.tenant_id
    result = await container.approve.handle(
        body, actor=principal.subject_id, correlation_id=uuid4().hex
    )
    return ObservabilityEnvelope(data=result, meta=_meta(started))
